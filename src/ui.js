// Zero-dependency aesthetic UI renderer (Linear / Raycast inspired minimalism)

export const colors = {
  reset: '\x1b[0m',
  bold: '\x1b[1m',
  dim: '\x1b[2m',
  zinc: '\x1b[38;2;228;228;231m',       // #e4e4e7 (crisp primary text)
  muted: '\x1b[38;2;161;161;170m',      // #a1a1aa (subtle secondary text)
  dimmed: '\x1b[38;2;113;113;122m',     // #71717a (tertiary quiet text)
  border: '\x1b[38;2;63;63;70m',        // #3f3f46 (subtle border)
  accent: '\x1b[38;2;165;180;252m',     // #a5b4fc (soft lavender/indigo)
  mint: '\x1b[38;2;110;231;183m',       // #6ee7b7 (soft mint green)
  ochre: '\x1b[38;2;253;224;71m',       // #fde047 (warm amber)
  rose: '\x1b[38;2;253;164;175m',       // #fda4af (soft rose)
  cyan: '\x1b[38;2;125;211;252m',       // #7dd3fc (sky cyan)

  // Backward compatibility
  white: '\x1b[38;2;228;228;231m',
  indigo: '\x1b[38;2;165;180;252m',
  terracotta: '\x1b[38;2;251;146;60m',
  emerald: '\x1b[38;2;110;231;183m',
  amber: '\x1b[38;2;253;224;71m',
  slate: '\x1b[38;2;161;161;170m',
  red: '\x1b[38;2;253;164;175m',
};

export function stripAnsi(str) {
  return String(str ?? '').replace(/\x1b\[[0-9;]*m/g, '');
}

export function formatTokenCount(n) {
  if (n >= 1_000_000_000) return `${(n / 1_000_000_000).toFixed(2)}B`;
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}M`;
  if (n >= 1_000) return `${(n / 1_000).toFixed(1)}K`;
  return String(n);
}

export function makePill(status) {
  const s = String(status || '').toLowerCase();
  if (s === 'active') return `${colors.mint}●${colors.reset} active`;
  if (s === 'standby') return `${colors.dimmed}○${colors.reset} standby`;
  if (s === 'rate_limited' || s === 'cooldown') return `${colors.ochre}◌${colors.reset} cooldown`;
  if (s === 'auth_expired' || s === 'expired') return `${colors.rose}✕${colors.reset} expired`;
  return `${colors.dimmed}· ${s}${colors.reset}`;
}

export function makeGauge(pctRemaining, width = 8) {
  if (pctRemaining === null || pctRemaining === undefined) return `${colors.dimmed}—${colors.reset}`;
  const pct = Math.max(0, Math.min(100, Math.round(pctRemaining)));
  const filled = Math.round((pct / 100) * width);
  const empty = width - filled;

  const barColor = pct > 40 ? colors.mint : pct > 15 ? colors.ochre : colors.rose;
  return `${barColor}${'▰'.repeat(filled)}${colors.border}${'▱'.repeat(empty)}${colors.reset} ${colors.zinc}${String(pct).padStart(3)}%${colors.reset}`;
}

export function renderPanel(title, lines, options = {}) {
  const width = options.width || 72;
  const innerWidth = width - 2;
  const titleColor = options.titleColor || colors.accent;
  const borderColor = options.borderColor || colors.border;

  const titleStr = title ? ` ${title} ` : '';
  const topDash = '─'.repeat(Math.max(0, innerWidth - titleStr.length - 2));
  const top = `${borderColor}╭─${titleColor}${colors.bold}${titleStr}${borderColor}${topDash}╮${colors.reset}`;
  const bottom = `${borderColor}╰${'─'.repeat(innerWidth)}╯${colors.reset}`;

  console.log(top);
  for (const line of lines) {
    if (line === null || line === undefined) {
      console.log(`${borderColor}│${' '.repeat(innerWidth)}│${colors.reset}`);
    } else {
      const plain = stripAnsi(line);
      const pad = Math.max(0, innerWidth - plain.length - 2);
      console.log(`${borderColor}│${colors.reset}  ${line}${' '.repeat(pad)}${borderColor}│${colors.reset}`);
    }
  }
  console.log(bottom);
}

// Clean aligned terminal table with rounded borders and subtle aesthetic
export function printTable(headers, rows) {
  const colWidths = headers.map((h, i) => {
    let max = stripAnsi(h.label).length;
    for (const row of rows) {
      const valStr = stripAnsi(row[i]);
      if (valStr.length > max) max = valStr.length;
    }
    return max + 2;
  });

  const sepTop = '╭' + colWidths.map(w => '─'.repeat(w)).join('┬') + '╮';
  const sepMid = '├' + colWidths.map(w => '─'.repeat(w)).join('┼') + '┤';
  const sepBot = '╰' + colWidths.map(w => '─'.repeat(w)).join('┴') + '╯';

  console.log(colors.border + sepTop + colors.reset);

  // Header row
  const headerStr = headers
    .map((h, i) => {
      const plainLen = stripAnsi(h.label).length;
      const pad = colWidths[i] - plainLen;
      return h.align === 'right' ? ' '.repeat(pad - 1) + h.label + ' ' : ' ' + h.label + ' '.repeat(pad - 1);
    })
    .join(colors.border + '│' + colors.reset);
  console.log(colors.border + '│' + colors.accent + headerStr + colors.border + '│' + colors.reset);
  console.log(colors.border + sepMid + colors.reset);

  // Rows
  for (const row of rows) {
    const rowStr = row
      .map((val, i) => {
        const raw = String(val ?? '');
        const plainLen = stripAnsi(raw).length;
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

  let remStr = '';
  if (activeAccount.quota && activeAccount.quota.sessionRemainingPct !== undefined) {
    const rem = activeAccount.quota.sessionRemainingPct;
    const color = rem > 30 ? colors.mint : colors.ochre;
    remStr = ` · ${color}${rem}% session left${colors.reset}`;
    if (activeAccount.quota.sessionReset) {
      remStr += ` ${colors.dimmed}(resets ${activeAccount.quota.sessionReset})${colors.reset}`;
    }
  } else if (activeAccount.email) {
    remStr = ` ${colors.dimmed}· ${activeAccount.email}${colors.reset}`;
  }

  console.log();
  renderPanel('claude-pool', [
    null,
    `${colors.mint}●${colors.reset} ${colors.bold}active${colors.reset}    ${colors.zinc}${activeAccount.name}${colors.reset} ${colors.dimmed}(P${activeAccount.priority})${colors.reset}${remStr}`,
    `${colors.dimmed}○${colors.reset} standby   ${colors.muted}${standbyNames}${colors.reset}`,
    `${colors.accent}◌${colors.reset} pool      ${colors.muted}${todayPoolStr} tokens today across ${standbyAccounts.length + 1} accounts${colors.reset}`,
    null,
  ]);
  console.log();
}

export function renderFailoverBanner(oldAccount, newAccount, sessionId) {
  console.log();
  renderPanel('failover transition', [
    null,
    `${colors.ochre}Rate limit reached on ${oldAccount.name}${colors.reset}`,
    sessionId ? `${colors.mint}●${colors.reset} preserved session    ${colors.muted}${sessionId.slice(0, 16)}...${colors.reset}` : null,
    `${colors.mint}●${colors.reset} synchronized state   ${colors.muted}${newAccount.name}${colors.reset}`,
    `${colors.accent}→${colors.reset} continuing on        ${colors.bold}${newAccount.name}${colors.reset} ${colors.dimmed}(priority ${newAccount.priority})${colors.reset}`,
    null,
  ], { titleColor: colors.ochre });
  console.log();
}
