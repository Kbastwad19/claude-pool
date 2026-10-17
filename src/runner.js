import { spawnSync } from 'child_process';
import path from 'path';
import os from 'os';
import { SessionSyncEngine } from './sessionSync.js';
import { MetricsEngine } from './metrics.js';
import { QuotaEngine } from './quota.js';
import { renderSessionHeader, renderFailoverBanner, colors } from './ui.js';

export class ProcessRunner {
  constructor(configManager) {
    this.configManager = configManager;
  }

  cleanEnvForAccount(account) {
    const env = { ...process.env };
    const defaultClaudePath = path.resolve(path.join(os.homedir(), '.claude'));

    if (path.resolve(account.configDir) !== defaultClaudePath) {
      env.CLAUDE_CONFIG_DIR = account.configDir;
    } else {
      delete env.CLAUDE_CONFIG_DIR;
    }

    // Clear overrides
    delete env.ANTHROPIC_BASE_URL;
    delete env.ANTHROPIC_API_KEY;
    delete env.ANTHROPIC_DEFAULT_SONNET_MODEL;
    delete env.CLAUDE_CODE_USE_BEDROCK;
    delete env.AWS_PROFILE;
    delete env.AWS_REGION;
    delete env.ANTHROPIC_DEFAULT_OPUS_MODEL;

    return env;
  }

  getReadyAccounts(accounts) {
    const now = Date.now() / 1000;
    return accounts
      .filter(a => a.enabled !== false && (!a.rateLimitedUntil || a.rateLimitedUntil < now))
      .sort((a, b) => a.priority - b.priority);
  }

  runSession(extraArgs = [], initialAccountName = null) {
    const accounts = this.configManager.loadAccounts();

    let activeAccount = null;
    if (initialAccountName) {
      activeAccount = accounts.find(a => a.name.toLowerCase() === initialAccountName.toLowerCase());
    }

    if (!activeAccount) {
      const ready = this.getReadyAccounts(accounts);
      activeAccount = ready[0] || null;
    }

    if (!activeAccount) {
      console.log(`${colors.red}No ready accounts found in Claude Pool!${colors.reset}`);
      console.log(`Run ${colors.indigo}claude-pool status${colors.reset} or ${colors.indigo}claude-pool setup${colors.reset} to configure accounts.`);
      return;
    }

    let resumeSessionId = null;
    for (let i = 0; i < extraArgs.length; i++) {
      if ((extraArgs[i] === '-r' || extraArgs[i] === '--resume') && i + 1 < extraArgs.length) {
        resumeSessionId = extraArgs[i + 1];
      }
    }

    while (activeAccount) {
      const readyAccounts = this.getReadyAccounts(accounts);
      const standbyAccounts = readyAccounts.filter(a => a.name !== activeAccount.name);
      const poolStats = MetricsEngine.getPoolStats(accounts);

      // Fast check quota cache
      QuotaEngine.fetchAllQuotas(accounts, false);

      renderSessionHeader(activeAccount, standbyAccounts, poolStats);

      const cmdArgs = [...extraArgs];
      if (resumeSessionId && !cmdArgs.includes('-r') && !cmdArgs.includes('--resume')) {
        cmdArgs.push('--resume', resumeSessionId);
      }

      const env = this.cleanEnvForAccount(activeAccount);

      let exitCode = 0;
      try {
        const proc = spawnSync('claude', cmdArgs, {
          env,
          stdio: 'inherit', // Full terminal passthrough
        });
        exitCode = proc.status !== null ? proc.status : 1;
      } catch (err) {
        console.log(`${colors.red}Error launching claude:${colors.reset} ${err.message}`);
        break;
      }

      if (exitCode === 0) {
        console.log(`\n${colors.emerald}✓ Claude session finished normally.${colors.reset}`);
        break;
      }

      // Non-zero exit code: check if rate limited and standby available
      const latestId = SessionSyncEngine.getLatestSessionId(activeAccount);
      if (latestId) {
        resumeSessionId = latestId;
      }

      if (standbyAccounts.length > 0) {
        const nextAccount = standbyAccounts[0];

        // Apply 1-hour cooldown
        activeAccount.rateLimitedUntil = Date.now() / 1000 + 3600;
        this.configManager.saveAccounts(accounts);

        let transferredId = null;
        if (resumeSessionId) {
          transferredId = SessionSyncEngine.transferSession(activeAccount, nextAccount, resumeSessionId);
        }

        renderFailoverBanner(activeAccount, nextAccount, transferredId || resumeSessionId);
        activeAccount = nextAccount;
        if (transferredId) {
          resumeSessionId = transferredId;
        }
      } else {
        console.log(`\n${colors.amber}⚠️ All accounts in pool are currently exhausted or unavailable.${colors.reset}`);
        break;
      }
    }
  }
}
