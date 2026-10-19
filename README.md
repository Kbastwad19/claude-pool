<div align="center">

# claude-pool

<p align="center">
  <strong>Multi-account token pooling and seamless failover manager for Claude Code CLI</strong>
</p>

<p align="center">
  <a href="https://www.npmjs.com/package/claude-pool"><img src="https://img.shields.io/npm/v/claude-pool.svg?style=flat-square&color=818cf8" alt="npm version" /></a>
  <a href="https://opensource.org/licenses/MIT"><img src="https://img.shields.io/badge/license-MIT-6ee7b7.svg?style=flat-square" alt="license" /></a>
  <a href="https://nodejs.org"><img src="https://img.shields.io/badge/node-%3E%3D18.0.0-fde047.svg?style=flat-square" alt="node version" /></a>
  <a href="https://github.com/Kbastwad19/claude-pool"><img src="https://img.shields.io/badge/dependencies-0-a1a1aa.svg?style=flat-square" alt="zero dependencies" /></a>
</p>

<p align="center">
  Pool multiple Claude subscriptions into one uninterrupted coding session with automated failover, cross-account transcript synchronization, and real-time quota telemetry.
</p>

<p align="center">
  <br />
  <img src="https://raw.githubusercontent.com/Kbastwad19/claude-pool/main/assets/demo.svg" alt="claude-pool live failover & session continuity demonstration" width="100%" style="max-width: 840px;" />
  <br />
</p>

</div>

---

## ⚡ Overview

Hitting Anthropic's **5-hour rolling limit or weekly cap** mid-flow interrupts your momentum:
- You have to halt your work.
- Manually log out and log in with another account.
- Lose your working session history and context.
- Guess blindly how much quota or token runway remains.

**`claude-pool` solves this completely.** It orchestrates your accounts by priority, tracks real-time quota meters, and **automatically migrates your active session transcript (`.jsonl`)** to standby accounts upon exhaustion. You stay locked in your flow without losing context.

```
                         ┌────────────────────────┐
                         │   Terminal / Editor    │
                         └───────────┬────────────┘
                                     │
                                     ▼
                         ┌────────────────────────┐
                         │      claude-pool       │
                         │  Priority Orchestrator │
                         └─────┬────────────┬─────┘
                               │            │
      ┌────────────────────────▼──┐      ┌──▼────────────────────────┐
      │   Account 1 (Primary)     │      │   Account 2 (Standby)     │
      │   Status: ● 5h cap hit    │      │   Status: ○ Resuming...   │
      └─────────────┬─────────────┘      └──▲────────────────────────┘
                    │                       │
                    └──── Session Sync ─────┘
                          <session>.jsonl
```

---

## ✨ Features

- **Continuous Memory Sync** — Automatically copies the active session transcript (`<session-id>.jsonl`) and tool sidecars to standby accounts. Continues instantly with `claude --resume`.
- **Zero-Touch Auto-Failover** — Catches rate-limit events live, applies cooling periods, and seamlessly re-spawns Claude on the next priority account.
- **In-Session Slash Commands** — Check `/pool-limits` or trigger `/pool-switch` directly inside Claude without exiting your session.
- **Quota & Countdown Telemetry** — Live gauges display exact `% session quota remaining` and humanized countdowns (e.g. `resets 2:09pm`).
- **Aggregated Token Telemetry** — Real-time consumption breakdown (Input, Output, Cache Read/Create) across all pooled accounts and models.
- **Linear/Raycast Terminal Aesthetic** — Minimalist, quiet UI with subtle status indicators (`● active`, `○ standby`), smooth gauges, and rounded panels.
- **Zero Dependencies** — Ultra-lightweight native Node.js package (~15KB unpacked). Downloads and runs instantly via `npx`.

---

## 🚀 Quick Start

### Option A: Instant Run via `npx` (Zero Installation)

```bash
# Guided 60-second account setup wizard
npx claude-pool setup

# Start coding with token pooling enabled
npx claude-pool
```

### Option B: Global Install (Recommended)

```bash
npm install -g claude-pool
```

Once installed globally, replace `claude` with `claude-pool`:

```bash
# Launch interactive session with pooling & failover
claude-pool

# Pass any regular Claude flags seamlessly
claude-pool --model opus
claude-pool -p "Fix failing unit tests in auth module"
```

---

## 🖥️ Terminal Interface

### 1. Launch HUD
Anchored at the start of every session:

```
╭─ claude-pool ────────────────────────────────────────────────────────╮
│                                                                      │
│  ● active    primary (P1) · 97% session left (resets 2:30pm)         │
│  ○ standby   account4, account2, bedrock                             │
│  ◌ pool      973.8K tokens today across 4 accounts                   │
│                                                                      │
╰──────────────────────────────────────────────────────────────────────╯
```

### 2. Auto-Failover Transition Card
When an account hits Anthropic's rolling limit, `claude-pool` captures state and migrates immediately:

```
╭─ failover transition ────────────────────────────────────────────────╮
│                                                                      │
│  Rate limit reached on primary                                       │
│  ● preserved session    4e00c501-e0c...                              │
│  ● synchronized state   account4                                     │
│  → continuing on        account4 (priority 1)                        │
│                                                                      │
╰──────────────────────────────────────────────────────────────────────╯
```

### 3. Live Quota Table (`claude-pool limits`)
```
╭──────────┬─────────┬───────────┬───────────────┬────────────────┬───────────────┬────────────────╮
│ Priority │ Account │ Status    │ Session Quota │ Session Resets │ Weekly Quota  │ Weekly Resets  │
├──────────┼─────────┼───────────┼───────────────┼────────────────┼───────────────┼────────────────┤
│ P1       │ primary │ ● active  │ ▰▰▰▰▰▰▱▱  71% │ Oct 19, 2:09pm │ ▰▰▰▰▰▰▰▱  88% │ Oct 25, 7:29pm │
│ P2       │ backup  │ ○ standby │ ▰▰▰▰▰▰▰▰ 100% │ Oct 19, 9:15pm │ ▰▰▰▰▰▱▱▱  53% │ Oct 24, 6:00pm │
╰──────────┴─────────┴───────────┴───────────────┴────────────────┴───────────────┴────────────────╯
```

### 4. Aggregated Token Dashboard (`claude-pool dashboard`)
```
╭─ token pool dashboard ──────────────────────────────────────────────╮
│                                                                      │
│  Today: 193.4M (944.2K out · 192.4M cache)   Lifetime: 6.68B         │
│                                                                      │
╰──────────────────────────────────────────────────────────────────────╯

╭──────────┬─────────┬───────────┬───────────────┬────────────────┬─────────────────────────┬──────────╮
│ Priority │ Account │ Status    │ Session Quota │ Today's Tokens │ Model Breakdown (Today) │ Sessions │
├──────────┼─────────┼───────────┼───────────────┼────────────────┼─────────────────────────┼──────────┤
│ P1       │ primary │ ● active  │ ▰▰▱▱▱▱▱▱  28% │         193.4M │ opus-5-5: 193.4M        │ 73       │
│ P2       │ backup  │ ○ standby │ ▰▰▰▰▰▰▰▰ 100% │              0 │ —                       │ 12       │
╰──────────┴─────────┴───────────┴───────────────┴────────────────┴─────────────────────────┴──────────╯
```

---

## ⚡ In-Session Commands

You never need to leave your active Claude session to inspect limits or switch accounts. `claude-pool` provisions unified slash commands across all pooled environments:

| Command | Action |
|---|---|
| **`/pool-limits`** | Prints real-time remaining 5-hour session & weekly quota percentages + reset countdowns right in your conversation. |
| **`/pool-switch [account]`** | Synchronizes conversation state to the target account and **automatically hot-restarts** Claude Code. If no account is specified, it rotates to the next standby account. |
| **`/pool`** | Renders the aggregated token pool consumption table and active account status. |

> **💡 Zero-Token Tip**: In any Claude Code session, starting a line with `!` executes directly in your local terminal without spending AI tokens:
> ```bash
> ! claude-pool limits
> ```

---

## ⌨️ CLI Command Reference

| Command | Description |
|---|---|
| `claude-pool` | Launch Claude session with active account & automatic failover |
| `claude-pool setup` | Interactive wizard to connect and authenticate all accounts |
| `claude-pool switch [account]` | Switch active account and synchronize session state |
| `claude-pool limits` | Inspect remaining session/weekly % quota and reset countdowns |
| `claude-pool dashboard` | Unified pool dashboard with today's consumption & gauges |
| `claude-pool usage [account]` | Detailed token breakdown (Input, Output, Cache) per account |
| `claude-pool priority` | View configured account priority ranking |
| `claude-pool set-priority <name> <p>` | Set priority rank for an account (e.g. `set-priority primary 1`) |
| `claude-pool status` | List configured accounts, directories, and health badges |
| `claude-pool check-auth` | Verify live authentication across all accounts |
| `claude-pool login <account>` | Re-authenticate an account whose OAuth session expired |
| `claude-pool add [name]` | Add a new account to the pool interactively |

---

## 🧠 Under The Hood

Claude Code stores project sessions as local JSONL transcripts:

```
~/<config_dir>/projects/<CWD-encoded>/<session-id>.jsonl
```

Where `<CWD-encoded>` safely escapes working directories:
- **Windows**: `E:\PP\accs` → `E--PP-accs`
- **POSIX**: `/home/user/project` → `-home-user-project`

When an account approaches or hits Anthropic's rate limits:
1. `claude-pool` detects the limit exit code or message.
2. Identifies the active `<session-id>` and project path.
3. Synchronizes `<session-id>.jsonl` and sidecar tool results into the next priority account's configuration directory.
4. Isolates configuration via `CLAUDE_CONFIG_DIR = ~/.claude-<account>`.
5. Relaunches `claude --resume <session-id>` with **zero loss of conversation memory**.

---

## 🛠️ FAQ

### What happens if an account's OAuth session expires?
OAuth tokens occasionally expire. Run:
```bash
claude-pool check-auth
```
If an account is flagged with `✕ expired`, re-authenticate it in your browser with:
```bash
claude-pool login <account_name>
```

### Can I use this with Python?
Yes! A Python implementation is also included in this repository. You can install via:
```bash
pip install claude-pool
```

---

## 📄 License

Distributed under the [MIT License](LICENSE).
