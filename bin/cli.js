#!/usr/bin/env node

import { ConfigManager } from '../src/config.js';
import { MetricsEngine } from '../src/metrics.js';
import { QuotaEngine } from '../src/quota.js';
import { ProcessRunner } from '../src/runner.js';
import { runSetupWizard, checkAuthStatus, runAccountLogin, ensureAllSlashCommands } from '../src/setup.js';
import { colors, formatTokenCount, makePill, makeGauge, printTable } from '../src/ui.js';

const KNOWN_COMMANDS = new Set([
  'start',
  'setup',
  'switch',
  'use',
  'limits',
  'remaining',
  'quota',
  'dashboard',
  'usage',
  'tokens',
  'priority',
  'set-priority',
  'status',
  'accounts',
  'check-auth',
  'login',
  'add',
  '--help',
  '-h',
]);

const args = process.argv.slice(2);
const firstArg = args[0];

const cfg = new ConfigManager();

async function handleCommand() {
  const accounts = cfg.loadAccounts();
  ensureAllSlashCommands(accounts);

  if (!firstArg || (!firstArg.startsWith('-') && !KNOWN_COMMANDS.has(firstArg))) {
    // Default: run interactive session with failover
    const runner = new ProcessRunner(cfg);
    runner.runSession(args);
    return;
  }

  switch (firstArg) {
    case 'start': {
      const runner = new ProcessRunner(cfg);
      runner.runSession(args.slice(1));
      break;
    }

    case 'setup': {
      await runSetupWizard();
      break;
    }

    case 'switch':
    case 'use': {
      let targetName = args[1];
      const accounts = cfg.loadAccounts();

      if (!targetName) {
        if (!process.stdin.isTTY || process.env.CLAUDE_PID || process.env.CLAUDECODE) {
          // Inside Claude session or non-interactive environment: auto-select next standby account
          const nextStandby = accounts.slice(1).find(a => a.enabled !== false);
          if (!nextStandby) {
            console.log(`${colors.red}No other enabled standby accounts found in pool.${colors.reset}`);
            return;
          }
          targetName = nextStandby.name;
          console.log(`${colors.dim}No target account specified. Rotating to next standby: ${colors.bold}${targetName}${colors.reset}`);
        } else {
          console.log(`\n${colors.indigo}${colors.bold}Switch Active Claude Account:${colors.reset}\n`);
          accounts.forEach((a, idx) => {
            const activeTag = idx === 0 ? `${colors.emerald} [ACTIVE]${colors.reset}` : '';
            const emailTag = a.email ? ` (${a.email})` : '';
            console.log(`  ${colors.bold}${idx + 1})${colors.reset} ${a.name}${emailTag}${activeTag}`);
          });
          console.log();
          const { default: readline } = await import('readline/promises');
          const rl = readline.createInterface({ input: process.stdin, output: process.stdout });
          const choice = await rl.question(`Select account (1-${accounts.length}): `);
          rl.close();
          const chosenIdx = parseInt(choice.trim(), 10) - 1;
          if (chosenIdx >= 0 && chosenIdx < accounts.length) {
            targetName = accounts[chosenIdx].name;
          } else {
            console.log(`${colors.red}Invalid selection.${colors.reset}`);
            return;
          }
        }
      }

      const prevActive = accounts[0];
      const target = accounts.find(a => a.name.toLowerCase() === targetName.toLowerCase());
      if (!target) {
        console.log(`${colors.red}Error: Account '${targetName}' not found in pool.${colors.reset}`);
        return;
      }

      target.rateLimitedUntil = null;
      cfg.updateAccountPriority(target.name, 1);

      if (prevActive && prevActive.name.toLowerCase() !== target.name.toLowerCase()) {
        const { SessionSyncEngine } = await import('../src/sessionSync.js');
        const syncedId = SessionSyncEngine.transferSession(prevActive, target);
        if (syncedId) {
          console.log(`${colors.emerald}✓ Synchronized active session (${syncedId.slice(0, 12)}...) to ${target.name}.${colors.reset}`);
        }
      }

      const claudePid = process.env.CLAUDE_PID || (process.env.CLAUDECODE ? process.ppid : null);
      if (claudePid && prevActive && prevActive.name.toLowerCase() !== target.name.toLowerCase()) {
        console.log(`\n${colors.emerald}✓ Active account is now: ${colors.bold}${target.name} (Priority 1)${colors.reset}`);
        console.log(`${colors.cyan}⚡ Auto-restarting Claude Code session on ${target.name}...${colors.reset}\n`);

        const { spawn } = await import('child_process');
        if (process.platform === 'win32') {
          const killer = spawn(
            'powershell.exe',
            ['-NoProfile', '-Command', `Start-Sleep -Milliseconds 400; Stop-Process -Id ${claudePid} -Force`],
            { detached: true, stdio: 'ignore' }
          );
          killer.unref();
        } else {
          const killer = spawn(
            'sh',
            ['-c', `sleep 0.4 && kill -TERM ${claudePid}`],
            { detached: true, stdio: 'ignore' }
          );
          killer.unref();
        }
      } else {
        console.log(`\n${colors.emerald}✓ Active account is now: ${colors.bold}${target.name} (Priority 1)${colors.reset}`);
        console.log(`${colors.dim}Run ${colors.reset}${colors.indigo}claude-pool${colors.reset}${colors.dim} to start working on ${target.name}.${colors.reset}\n`);
      }
      break;
    }

    case 'limits':
    case 'remaining':
    case 'quota': {
      console.log(`\n${colors.indigo}Querying live Claude usage quotas & reset countdowns...${colors.reset}`);
      const accounts = cfg.loadAccounts();
      const force = args.includes('-r') || args.includes('--refresh');
      QuotaEngine.fetchAllQuotas(accounts, force);

      const headers = [
        { label: 'Rank', align: 'center' },
        { label: 'Priority', align: 'center' },
        { label: 'Account' },
        { label: 'Status', align: 'center' },
        { label: 'Session Remaining' },
        { label: 'Session Resets At' },
        { label: 'Weekly Remaining' },
        { label: 'Weekly Resets At' },
      ];

      const rows = accounts.map((a, i) => [
        i === 0 ? '#1' : `#${i + 1}`,
        `P${a.priority}`,
        a.name,
        makePill(i === 0 ? 'active' : 'standby'),
        a.quota ? makeGauge(a.quota.sessionRemainingPct) : `${colors.dim}—${colors.reset}`,
        a.quota?.sessionReset || '—',
        a.quota ? makeGauge(a.quota.weekRemainingPct) : `${colors.dim}—${colors.reset}`,
        a.quota?.weekReset || '—',
      ]);

      console.log(`\n${colors.indigo}${colors.bold}Pool Quota & Remaining Usage${colors.reset}`);
      printTable(headers, rows);
      console.log();
      break;
    }

    case 'dashboard': {
      const accounts = cfg.loadAccounts();
      const stats = MetricsEngine.getPoolStats(accounts);
      QuotaEngine.fetchAllQuotas(accounts, false);

      console.log();
      console.log(colors.border + '┌─ ' + colors.indigo + colors.bold + 'Token Pool Dashboard' + colors.border + ' ─'.repeat(45) + '┐' + colors.reset);
      console.log(colors.border + '│' + colors.reset + `  Today's Pool: ${colors.emerald}${colors.bold}${formatTokenCount(stats.todayPoolTokens)}${colors.reset} │ Output: ${colors.terracotta}${formatTokenCount(stats.todayPoolOutput)}${colors.reset} │ Cache: ${colors.indigo}${formatTokenCount(stats.todayPoolCache)}${colors.reset} │ Lifetime: ${colors.bold}${formatTokenCount(stats.lifetimePoolCache + stats.lifetimePoolOutput)}${colors.reset}`);
      console.log(colors.border + '└' + '─'.repeat(68) + '┘' + colors.reset);
      console.log();

      const headers = [
        { label: 'Priority', align: 'center' },
        { label: 'Account' },
        { label: 'Status', align: 'center' },
        { label: 'Remaining Quota' },
        { label: "Today's Tokens", align: 'right' },
        { label: 'Model Breakdown (Today)' },
        { label: 'Sessions', align: 'center' },
      ];

      const rows = stats.accounts.map((s, i) => {
        const acct = accounts.find(a => a.name === s.accountName) || { priority: 99 };
        const bdown = Object.entries(s.todayTokensByModel)
          .map(([m, t]) => `${m.replace('claude-', '')}: ${formatTokenCount(t)}`)
          .join(' · ') || '—';

        return [
          `P${acct.priority}`,
          s.accountName,
          makePill(i === 0 ? 'active' : 'standby'),
          acct.quota ? makeGauge(acct.quota.sessionRemainingPct, 8) : `${colors.dim}—${colors.reset}`,
          `${colors.bold}${formatTokenCount(s.todayTotalTokens)}${colors.reset}`,
          `${colors.slate}${bdown}${colors.reset}`,
          String(s.totalSessions),
        ];
      });

      printTable(headers, rows);
      console.log(`${colors.dim}Tip: Run ${colors.reset}${colors.indigo}claude-pool limits${colors.reset}${colors.dim} to inspect reset countdowns & weekly quotas.${colors.reset}\n`);
      break;
    }

    case 'usage':
    case 'tokens': {
      const targetName = args[1];
      const accounts = cfg.loadAccounts();

      const targets = targetName
        ? accounts.filter(a => a.name.toLowerCase() === targetName.toLowerCase())
        : accounts;

      if (targets.length === 0) {
        console.log(`${colors.red}Account '${targetName}' not found in pool.${colors.reset}`);
        return;
      }

      for (const acct of targets) {
        const stat = MetricsEngine.readAccountStats(acct);
        console.log();
        console.log(colors.border + '┌─ ' + colors.indigo + colors.bold + `Token Breakdown: ${acct.name}` + colors.border + ' ─'.repeat(45) + '┐' + colors.reset);
        console.log(colors.border + '│' + colors.reset + `  Account: ${colors.bold}${acct.name}${colors.reset} [Priority ${acct.priority}] ${colors.slate}· ${acct.email || acct.configDir}${colors.reset}`);
        console.log(colors.border + '└' + '─'.repeat(71) + '┘' + colors.reset);

        const headers = [
          { label: 'Model' },
          { label: 'Input Tokens', align: 'right' },
          { label: 'Output Tokens', align: 'right' },
          { label: 'Cache Read', align: 'right' },
          { label: 'Cache Create', align: 'right' },
          { label: 'Total Tokens', align: 'right' },
        ];

        const rows = Object.entries(stat.todayModelsDetail).map(([model, u]) => [
          model,
          u.input.toLocaleString(),
          u.output.toLocaleString(),
          u.cacheRead.toLocaleString(),
          u.cacheCreate.toLocaleString(),
          `${colors.bold}${u.total.toLocaleString()} (${formatTokenCount(u.total)})${colors.reset}`,
        ]);

        if (rows.length === 0) {
          rows.push(['No activity today', '0', '0', '0', '0', '0']);
        }

        console.log(`\n${colors.emerald}${colors.bold}Today's Usage (Total: ${formatTokenCount(stat.todayTotalTokens)})${colors.reset}`);
        printTable(headers, rows);
        console.log();
      }
      break;
    }

    case 'priority': {
      const accounts = cfg.loadAccounts();
      const headers = [
        { label: 'Rank', align: 'center' },
        { label: 'Priority', align: 'center' },
        { label: 'Account' },
        { label: 'Status', align: 'center' },
        { label: 'Email' },
        { label: 'Config Directory' },
      ];
      const rows = accounts.map((a, i) => [
        i === 0 ? '#1' : `#${i + 1}`,
        `P${a.priority}`,
        a.name,
        makePill(i === 0 ? 'active' : 'standby'),
        a.email || '—',
        a.configDir,
      ]);
      console.log(`\n${colors.indigo}${colors.bold}Account Priority Ranking${colors.reset}`);
      printTable(headers, rows);
      console.log();
      break;
    }

    case 'set-priority': {
      const name = args[1];
      const prio = parseInt(args[2], 10);
      if (!name || isNaN(prio)) {
        console.log(`${colors.red}Usage: claude-pool set-priority <account_name> <priority_number>${colors.reset}`);
        return;
      }
      if (cfg.updateAccountPriority(name, prio)) {
        console.log(`${colors.emerald}✓ Priority for '${name}' set to P${prio}.${colors.reset}`);
      } else {
        console.log(`${colors.red}Error: Account '${name}' not found.${colors.reset}`);
      }
      break;
    }

    case 'status':
    case 'accounts': {
      const accounts = cfg.loadAccounts();
      const headers = [
        { label: 'Rank', align: 'center' },
        { label: 'Priority', align: 'center' },
        { label: 'Account' },
        { label: 'Status', align: 'center' },
        { label: 'Email' },
        { label: 'Plan' },
        { label: 'Config Directory' },
      ];
      const rows = accounts.map((a, i) => [
        i === 0 ? '#1' : `#${i + 1}`,
        `P${a.priority}`,
        a.name,
        makePill(i === 0 ? 'active' : 'standby'),
        a.email || '—',
        a.subscriptionType || '—',
        a.configDir,
      ]);
      printTable(headers, rows);
      console.log();
      break;
    }

    case 'check-auth': {
      console.log(`\n${colors.indigo}Checking live authentication status across all accounts...${colors.reset}`);
      const accounts = cfg.loadAccounts();
      for (const a of accounts) {
        const st = checkAuthStatus(a.configDir);
        a.email = st.email;
        a.subscriptionType = st.plan;
      }
      cfg.saveAccounts(accounts);
      console.log(`${colors.emerald}✓ Authentication check complete.${colors.reset}\n`);

      const headers = [
        { label: 'Rank', align: 'center' },
        { label: 'Priority', align: 'center' },
        { label: 'Account' },
        { label: 'Status', align: 'center' },
        { label: 'Email' },
        { label: 'Plan' },
      ];
      const rows = accounts.map((a, i) => [
        i === 0 ? '#1' : `#${i + 1}`,
        `P${a.priority}`,
        a.name,
        makePill(a.email ? (i === 0 ? 'active' : 'standby') : 'auth_expired'),
        a.email || '—',
        a.subscriptionType || '—',
      ]);
      printTable(headers, rows);
      console.log();
      break;
    }

    case 'login': {
      const name = args[1];
      if (!name) {
        console.log(`${colors.red}Usage: claude-pool login <account_name>${colors.reset}`);
        return;
      }
      const accounts = cfg.loadAccounts();
      const target = accounts.find(a => a.name.toLowerCase() === name.toLowerCase());
      if (!target) {
        console.log(`${colors.red}Account '${name}' not found.${colors.reset}`);
        return;
      }
      runAccountLogin(target.configDir);
      const st = checkAuthStatus(target.configDir);
      if (st.ok) {
        target.email = st.email;
        target.subscriptionType = st.plan;
        cfg.saveAccounts(accounts);
        console.log(`${colors.emerald}✓ Account '${target.name}' authenticated as ${st.email}.${colors.reset}`);
      }
      break;
    }

    case '--help':
    case '-h': {
      console.log(`
${colors.indigo}${colors.bold}Claude Pool${colors.reset} — Multi-account token pooling and seamless failover manager

${colors.bold}USAGE:${colors.reset}
  npx claude-pool [COMMAND] [ARGS...]
  claude-pool [COMMAND] [ARGS...]

${colors.bold}COMMANDS:${colors.reset}
  ${colors.indigo}claude-pool${colors.reset}                  Launch Claude session with pooled accounts & auto-failover
  ${colors.indigo}claude-pool switch [acct]${colors.reset}    Manually switch active account (or interactive picker)
  ${colors.indigo}claude-pool setup${colors.reset}            Guided setup wizard to connect accounts from scratch
  ${colors.indigo}claude-pool limits${colors.reset}           Inspect remaining session/weekly % quota & reset timers
  ${colors.indigo}claude-pool dashboard${colors.reset}        Real-time aggregated token metrics & model stats
  ${colors.indigo}claude-pool usage [acct]${colors.reset}     Detailed token breakdown (input, output, cache) per account
  ${colors.indigo}claude-pool priority${colors.reset}         View or reorder account priority order
  ${colors.indigo}claude-pool set-priority <name> <p>${colors.reset} Set priority rank for an account
  ${colors.indigo}claude-pool status${colors.reset}           List configured accounts & health badges
  ${colors.indigo}claude-pool check-auth${colors.reset}       Verify live authentication across all accounts
  ${colors.indigo}claude-pool login <acct>${colors.reset}     Re-authenticate an expired account in browser
`);
      break;
    }

    default: {
      // Pass through any other arguments directly to Claude Code
      const runner = new ProcessRunner(cfg);
      runner.runSession(args);
      break;
    }
  }
}

handleCommand().catch(err => {
  console.error(`${colors.red}Error:${colors.reset}`, err.message);
  process.exit(1);
});
