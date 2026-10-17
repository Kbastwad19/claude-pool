// Zero-dependency aesthetic UI renderer (Linear / Raycast inspired)

export const colors = {
  reset: '\x1b[0m',
  bold: '\x1b[1m',
  dim: '\x1b[2m',
  white: '\x1b[37m',
  indigo: '\x1b[38;2;129;140;248m', // #818cf8
  terracotta: '\x1b[38;2;249;115;22m', // #f97316
  emerald: '\x1b[38;2;16;185;129m', // #10b981
  amber: '\x1b[38;2;245;158;11m', // #f59e0b
  slate: '\x1b[38;2;100;116;139m', // #64748b
  border: '\x1b[38;2;51;65;85m', // #334155
  red: '\x1b[38;2;239;68;68m', // #ef4444
  bgEmerald: '\x1b[48;2;16;185;129m\x1b[30m\x1b[1m',
  bgSlate: '\x1b[48;2;100;116;139m\x1b[37m\x1b[1m',
  bgAmber: '\x1b[48;2;245;158;11m\x1b[30m\x1b[1m',
  bgRed: '\x1b[48;2;239;68;68m\x1b[37m\x1b[1m',
};

export function formatTokenCount(n) {
  if (n >= 1_000_000_000) return `${(n / 1_000_000_000).toFixed(2)}B`;
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}M`;
  if (n >= 1_000) return `${(n / 1_000).toFixed(1)}K`;
  return String(n);
}

export function makePill(status) {
  if (status === 'active') return `${colors.bgEmerald} ACTIVE ${colors.reset}`;
  if (status === 'standby') return `${colors.bgSlate} STANDBY ${colors.reset}`;
  if (status === 'rate_limited') return `${colors.bgAmber} COOLDOWN ${colors.reset}`;
  if (status === 'auth_expired') return `${colors.bgRed} EXPIRED ${colors.reset}`;
  return `${colors.dim} ${status.toUpperCase()} ${colors.reset}`;
}

export function makeGauge(pctRemaining, width = 10) {
  if (pctRemaining === null || pctRemaining === undefined) return `${colors.dim}—${colors.reset}`;
  const pct = Math.max(0, Math.min(100, Math.round(pctRemaining)));
  const filled = Math.round((pct / 100) * width);
  const empty = width - filled;

  const barColor = pct > 40 ? colors.emerald : pct > 15 ? colors.amber : colors.red;
  return `${barColor}${'█'.repeat(filled)}${colors.border}${'░'.repeat(empty)} ${pct}%${colors.reset}`;
}

// Clean aligned terminal table without external dependencies
export function printTable(headers, rows) {
  const colWidths = headers.map((h, i) => {
    let max = h.label.length;
    for (const row of rows) {
      const valStr = String(row[i] || '').replace(/\x1b\[[0-9;]*m/g, ''); // strip ansi
      if (valStr.length > max) max = valStr.length;
    }
    return max + 2;
  });

  const sepTop = '┌' + colWidths.map(w => '─'.repeat(w)).join('┬') + '┐';
  const sepMid = '├' + colWidths.map(w => '─'.repeat(w)).join('┼') + '┤';
  const sepBot = '└' + colWidths.map(w => '─'.repeat(w)).join('┴') + '┘';

  console.log(colors.border + sepTop + colors.reset);

  // Header row
  const headerStr = headers
    .map((h, i) => {
      const pad = colWidths[i] - h.label.length;
      return h.align === 'right' ? ' '.repeat(pad - 1) + h.label + ' ' : ' ' + h.label + ' '.repeat(pad - 1);
    })
    .join(colors.border + '│' + colors.reset);
  console.log(colors.border + '│' + colors.indigo + colors.bold + headerStr + colors.border + '│' + colors.reset);
  console.log(colors.border + sepMid + colors.reset);

  // Rows
  for (const row of rows) {
    const rowStr = row
      .map((val, i) => {
        const raw = String(val || '');
        const plainLen = raw.replace(/\x1b\[[0-9;]*m/g, '').length;
        const pad = Math.max(0, colWidths[i] - plainLen);
        const align = headers[i]?.align || 'left';
        return align === 'right' ? ' '.repeat(pad - 1) + raw + ' ' : ' ' + raw + ' '.repeat(pad - 1);
      })
      .join(colors.border + '│' + colors.reset);
    console.log(colors.border + '│' + colors.reset + rowStr + colors.border + '│' + colors.reset);
  }

  console.log(colors.border + sepBot + colors.reset);
}

export function renderSessionHeader(activeAccount, standbyAccounts, poolStats) {
  const standbyNames = standbyAccounts.length > 0 ? standbyAccounts.map(a => a.name).join(', ') : 'none';
  const todayPoolStr = poolStats ? formatTokenCount(poolStats.todayPoolTokens) : '0';

  console.log();
  console.log(colors.border + '┌─ ' + colors.indigo + colors.bold + 'claude-pool' + colors.border + ' ─'.repeat(60) + '┐' + colors.reset);
  
  let remStr = '';
  if (activeAccount.quota && activeAccount.quota.sessionRemainingPct !== undefined) {
    const rem = activeAccount.quota.sessionRemainingPct;
    const color = rem > 30 ? colors.emerald : colors.amber;
    remStr = ` · ${color}${colors.bold}${rem}% remaining${colors.reset}`;
    if (activeAccount.quota.sessionReset) {
      remStr += ` ${colors.slate}(resets ${activeAccount.quota.sessionReset})${colors.reset}`;
    }
  } else if (activeAccount.email) {
    remStr = ` ${colors.slate}· ${activeAccount.email}${colors.reset}`;
  }

  console.log(colors.border + '│' + colors.reset + `   ${colors.indigo}Active Account${colors.reset}   ${colors.bold}${activeAccount.name}${colors.reset} [Priority ${activeAccount.priority}]${remStr}`);
  console.log(colors.border + '│' + colors.reset + `   ${colors.indigo}Pool Today${colors.reset}       ${colors.bold}${todayPoolStr} tokens${colors.reset} ${colors.slate}across ${standbyAccounts.length + 1} accounts${colors.reset}`);
  console.log(colors.border + '│' + colors.reset + `   ${colors.indigo}Standby Queue${colors.reset}    ${standbyNames}`);
  console.log(colors.border + '└' + '─'.repeat(73) + '┘' + colors.reset);
  console.log();
}

export function renderFailoverBanner(oldAccount, newAccount, sessionId) {
  console.log();
  console.log(colors.terracotta + '╭─ Auto-Failover Transition ' + '─'.repeat(45) + '╮' + colors.reset);
  console.log(colors.terracotta + '│' + colors.reset + `  ${colors.amber}${colors.bold}Rate limit reached on ${oldAccount.name}${colors.reset}`);
  console.log(colors.terracotta + '│' + colors.reset);
  if (sessionId) {
    console.log(colors.terracotta + '│' + colors.reset + `  ${colors.emerald}✓ Preserved active session:${colors.reset} ${sessionId.slice(0, 16)}...`);
  }
  console.log(colors.terracotta + '│' + colors.reset + `  ${colors.emerald}✓ Synchronized project state to${colors.reset} ${newAccount.name}`);
  console.log(colors.terracotta + '│' + colors.reset + `  ${colors.indigo}→ Continuing on ${newAccount.name} (Priority ${newAccount.priority})${colors.reset}`);
  console.log(colors.terracotta + '╰' + '─'.repeat(72) + '╯' + colors.reset);
  console.log();
}
