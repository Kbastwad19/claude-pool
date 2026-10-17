import { spawnSync } from 'child_process';
import readline from 'readline/promises';
import fs from 'fs';
import path from 'path';
import os from 'os';
import { ConfigManager } from './config.js';
import { colors, printTable, makePill } from './ui.js';

export function checkClaudeCliInstalled() {
  try {
    const isWin = process.platform === 'win32';
    const cmd = isWin ? 'where.exe' : 'which';
    const res = spawnSync(cmd, ['claude'], { encoding: 'utf8' });
    return res.status === 0;
  } catch {
    return false;
  }
}

export function runAccountLogin(configDir, email = null) {
  const env = { ...process.env };
  const defaultClaudePath = path.resolve(path.join(os.homedir(), '.claude'));
  if (path.resolve(configDir) !== defaultClaudePath) {
    env.CLAUDE_CONFIG_DIR = configDir;
  } else {
    delete env.CLAUDE_CONFIG_DIR;
  }

  delete env.ANTHROPIC_BASE_URL;
  delete env.ANTHROPIC_API_KEY;
  delete env.ANTHROPIC_DEFAULT_SONNET_MODEL;

  const cmdArgs = ['auth', 'login'];
  if (email) cmdArgs.push('--email', email);

  console.log(`${colors.dim}Opening Claude browser authentication...${colors.reset}`);
  const res = spawnSync('claude', cmdArgs, { env, stdio: 'inherit' });
  return res.status === 0;
}

export function checkAuthStatus(configDir) {
  const env = { ...process.env };
  const defaultClaudePath = path.resolve(path.join(os.homedir(), '.claude'));
  if (path.resolve(configDir) !== defaultClaudePath) {
    env.CLAUDE_CONFIG_DIR = configDir;
  } else {
    delete env.CLAUDE_CONFIG_DIR;
  }

  try {
    const res = spawnSync('claude', ['auth', 'status'], { env, encoding: 'utf8', timeout: 10000 });
    if (res.status === 0) {
      const data = JSON.parse(res.stdout);
      return { ok: data.loggedIn === true, email: data.email, plan: data.subscriptionType };
    }
  } catch {}
  return { ok: false, email: null, plan: null };
}

export function installSlashCommands(configDir) {
  const cmdDir = path.join(configDir, 'commands');
  try {
    fs.mkdirSync(cmdDir, { recursive: true });
    // /pool
    fs.writeFileSync(
      path.join(cmdDir, 'pool.md'),
      '---\ndescription: View Claude Pool token dashboard and status\n---\nHere is the live Claude Pool token dashboard:\n!`claude-pool dashboard`\n',
      'utf8'
    );
    // /limits
    fs.writeFileSync(
      path.join(cmdDir, 'limits.md'),
      '---\ndescription: View remaining session and weekly quotas across all accounts in the pool\n---\nHere are the live Claude Pool quota metrics and limits:\n!`claude-pool limits`\n',
      'utf8'
    );
    // /switch
    fs.writeFileSync(
      path.join(cmdDir, 'switch.md'),
      '---\ndescription: Switch active Claude account in the pool\n---\n!`claude-pool switch $ARGUMENTS`\n\nIf the switch was successful, inform the user their active session was synchronized and they can run `/exit` to restart immediately on the newly active account.\n',
      'utf8'
    );
    // Also include /pool-limits and /pool-switch aliases
    fs.copyFileSync(path.join(cmdDir, 'limits.md'), path.join(cmdDir, 'pool-limits.md'));
    fs.copyFileSync(path.join(cmdDir, 'switch.md'), path.join(cmdDir, 'pool-switch.md'));
  } catch {}
}

export function ensureAllSlashCommands(accounts = []) {
  try {
    installSlashCommands(path.join(os.homedir(), '.claude'));
    for (const a of accounts) {
      if (a && a.configDir) installSlashCommands(a.configDir);
    }
    // Also install to current working directory .claude if it exists or in project
    const localClaudeDir = path.join(process.cwd(), '.claude');
    installSlashCommands(localClaudeDir);
  } catch {}
}

export async function runSetupWizard() {
  const rl = readline.createInterface({ input: process.stdin, output: process.stdout });

  console.log();
  console.log(colors.indigo + colors.bold + '╭─ claude-pool setup ' + '─'.repeat(45) + '╮' + colors.reset);
  console.log(colors.border + '│' + colors.reset + `  ${colors.bold}Welcome to Claude Pool Setup Wizard${colors.reset}`);
  console.log(colors.border + '│' + colors.reset + `  Connect multiple Claude subscriptions into one unified token pool.`);
  console.log(colors.border + '│' + colors.reset + `  ${colors.terracotta}Automatic failover · Continuous session memory · Live token metrics${colors.reset}`);
  console.log(colors.indigo + colors.bold + '╰' + '─'.repeat(66) + '╯' + colors.reset);
  console.log();

  if (!checkClaudeCliInstalled()) {
    console.log(`${colors.red}✗ Claude Code CLI was not found in your PATH.${colors.reset}`);
    console.log(`Please install Claude Code CLI first by running:\n`);
    console.log(`  ${colors.indigo}npm install -g @anthropic-ai/claude-code${colors.reset}\n`);
    console.log(`Once installed, run ${colors.indigo}claude-pool setup${colors.reset} again.`);
    rl.close();
    return;
  }

  console.log(`${colors.emerald}✓ Claude Code CLI detected.${colors.reset}`);

  const cfg = new ConfigManager();
  const accounts = [];
  const home = os.homedir();

  // Primary Account
  const primaryDir = path.join(home, '.claude');
  fs.mkdirSync(primaryDir, { recursive: true });
  console.log(`\n${colors.indigo}${colors.bold}Account #1 (Primary):${colors.reset}`);

  const primaryStatus = checkAuthStatus(primaryDir);
  if (primaryStatus.ok) {
    console.log(`  ${colors.emerald}✓ Already authenticated as:${colors.reset} ${colors.bold}${primaryStatus.email || 'Logged In'}${colors.reset}`);
    accounts.push({
      name: 'primary',
      configDir: primaryDir,
      priority: 1,
      enabled: true,
      email: primaryStatus.email,
      subscriptionType: primaryStatus.plan,
    });
  } else {
    const doLogin = await rl.question('  No active session in ~/.claude. Log in now? [Y/n]: ');
    if (doLogin.toLowerCase() !== 'n') {
      const email = await rl.question('  Enter email (optional, press Enter to skip): ');
      runAccountLogin(primaryDir, email.trim() || null);
      const st = checkAuthStatus(primaryDir);
      accounts.push({
        name: 'primary',
        configDir: primaryDir,
        priority: 1,
        enabled: true,
        email: st.email,
        subscriptionType: st.plan,
      });
    }
  }

  // Standby Accounts
  let count = 2;
  while (true) {
    console.log();
    const addMore = await rl.question(`Would you like to add another Claude account? [y/N]: `);
    if (addMore.trim().toLowerCase() !== 'y') break;

    const defaultName = `account${count}`;
    const nameInput = await rl.question(`  Enter account name [default: ${defaultName}]: `);
    const acctName = nameInput.trim() || defaultName;

    const acctDir = path.join(home, `.claude-${acctName}`);
    fs.mkdirSync(acctDir, { recursive: true });

    const st = checkAuthStatus(acctDir);
    let email = st.email;
    let plan = st.plan;

    if (st.ok) {
      console.log(`  ${colors.emerald}✓ Already authenticated as:${colors.reset} ${colors.bold}${email}${colors.reset}`);
    } else {
      console.log(`  Opening browser to sign in for '${acctName}'...`);
      const emailInput = await rl.question('  Enter email (optional, press Enter to skip): ');
      runAccountLogin(acctDir, emailInput.trim() || null);
      const newSt = checkAuthStatus(acctDir);
      email = newSt.email;
      plan = newSt.plan;
    }

    accounts.push({
      name: acctName,
      configDir: acctDir,
      priority: count,
      enabled: true,
      email,
      subscriptionType: plan,
    });
    count++;
  }

  rl.close();

  if (accounts.length > 0) {
    for (const a of accounts) {
      installSlashCommands(a.configDir);
    }
    cfg.saveAccounts(accounts);
    console.log(`\n${colors.emerald}✓ Setup complete! Your Claude Pool is configured:${colors.reset}\n`);

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
      a.email || '-',
      a.subscriptionType || '-',
      a.configDir,
    ]);
    printTable(headers, rows);

    console.log(`\nTo start coding with automated pooling, simply run:\n  ${colors.indigo}${colors.bold}claude-pool${colors.reset}\n`);
  }
}
