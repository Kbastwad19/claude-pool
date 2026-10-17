# 🔄 Claude Pool (`claude-pool`)

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](https://opensource.org/licenses/MIT)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![Claude Code](https://img.shields.io/badge/Claude%20Code-Compatible-orange.svg)](https://claude.ai/code)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

> **Pool multiple Claude subscriptions into one uninterrupted coding session with automated failover, live quota gauges, and cross-account memory sync.**

---

## ⚡ The Problem

If you have multiple Claude subscriptions (personal, work, backup), hitting Anthropic's **5-hour rolling limit or weekly cap** mid-flow is painful:
1. You have to stop work.
2. Manually log out and log in with your other account.
3. Lose conversation context and file history.
4. Guess how many tokens or remaining quota you have left across accounts.

**`claude-pool` solves this completely.** It pools your accounts with customizable priority, monitors your limits in real-time, and **automatically transfers your active session transcript to your standby account** when one hits a limit. You never lose your flow.

---

## ✨ Features

- 🔄 **Seamless Session Continuity**: Automatically syncs active project transcripts (`<session-id>.jsonl`) to the standby account and resumes via `claude --resume`. No lost memory.
- 🎯 **Priority-Based Scheduling**: Strictly prioritize accounts (e.g. `Primary` → `Account 2` → `Account 3`).
- 📊 **Real-time Token Metrics**: Live token aggregation directly from active sessions (Input, Output, Cache Read/Create, per model).
- ⏳ **Quota & Countdown Tracking**: Real-time gauge bars showing exact `% session quota remaining` and reset timers (e.g. `resets at 7:10pm`).
- 🎨 **Minimalist Aesthetic UI**: Linear & Raycast-inspired terminal UI with clean pill badges and subtle borders.
- 🧙 **Zero-Friction Setup Wizard**: Run `claude-pool setup` to connect and authenticate all your accounts in 60 seconds.

---

## 🚀 Quick Start (Zero-Setup with `npx`)

Since every Claude Code user already has Node.js and npm installed, you can run `claude-pool` instantly **with zero installation**:

```bash
# Run setup wizard directly via npx:
npx claude-pool setup

# Or start pooled session:
npx claude-pool
```

### Install Globally (Recommended, exactly like `codeburn`)

```bash
npm install -g claude-pool
```

Now `claude-pool` is available anywhere in your terminal:
```bash
claude-pool
```

*(Python users can also install via `pip install claude-pool`)*

The interactive wizard will:
- Detect your primary account (`~/.claude`).
- Guide you to add your secondary/standby Claude accounts.
- Open your browser to authenticate each account safely into isolated directories (`~/.claude-account2`, etc.).
- Set your priority rankings.

### 3. Start Coding!

Instead of typing `claude`, simply type:

```bash
claude-pool
```

You can pass any standard Claude flags:
```bash
claude-pool --model opus
claude-pool -p "Summarize git diff"
```

---

## 🖥️ Terminal Experience

### 1. Launch HUD Header
Anchored at the top of every session:
```
┌─  claude-pool  ─────────────────────────────────────────────────────────────┐
│   Active Account   primary [Priority 1] · 71% remaining (resets 7:10pm)     │
│   Pool Today       121.4M tokens across 3 accounts                          │
│   Standby Queue    account2, account3                                       │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 2. Live Failover Transition Card
When an account reaches its 5-hour limit, `claude-pool` catches it and migrates the session:
```
╭─ Auto-Failover Transition ──────────────────────────────────────────────────╮
│  Rate limit reached on primary                                              │
│                                                                             │
│  + Preserved active session: 6f1ff60d-9bb...                                │
│  + Synchronized project state to account2                                   │
│  -> Continuing on account2 (Priority 2)                                     │
╰─────────────────────────────────────────────────────────────────────────────╯
```

### 3. Unified Pool Dashboard (`claude-pool dashboard`)
```
┌─  Token Pool Dashboard  ────────────────────────────────────────────────────┐
│ Today's Pool Total: 121.4M   │ Output: 941.2K   │ Cache: 120.4M             │
└─────────────────────────────────────────────────────────────────────────────┘
┌────┬──────────┬─────────┬──────────────┬───────────┬──────────────────┬─────┐
│    │ Account  │ Status  │ Rem. Quota   │   Today's │ Model Breakdown  │ Ses │
├────┼──────────┼─────────┼──────────────┼───────────┼──────────────────┼─────┤
│ P1 │ primary  │  ACTIVE │ ██████░░ 71% │    118.0M │ opus-5-5: 118.0M │ 50  │
│ P2 │ account2 │ STANDBY │ ███████░ 93% │      3.4M │ fable-5-1: 3.4M  │ 46  │
│ P3 │ account3 │ STANDBY │ ████████ 99% │         0 │ -                │ 12  │
└────┴──────────┴─────────┴──────────────┴───────────┴──────────────────┴─────┘
```

---

## ⌨️ CLI Command Reference

| Command | Description |
|---|---|
| `claude-pool` | Launch Claude session with active account & auto-failover |
| `claude-pool setup` | Interactive wizard to connect all accounts from scratch |
| `claude-pool limits` / `remaining` | View exact % session and weekly quota remaining + reset countdowns |
| `claude-pool dashboard` | Unified pool dashboard with today's consumption & gauges |
| `claude-pool usage [account]` | Deep token breakdown (Input, Output, Cache Read/Create) per account |
| `claude-pool priority` | View priority order of accounts |
| `claude-pool set-priority <name> <p>` | Change account priority (e.g. `set-priority primary 1`) |
| `claude-pool priority --order a,b,c` | Reorder all accounts in one command |
| `claude-pool status` / `accounts` | List all accounts, directories, and health badges |
| `claude-pool check-auth` | Verify live authentication status across all accounts |
| `claude-pool login <account>` | Re-authenticate an account whose OAuth session expired |
| `claude-pool add [name]` | Add a new account to the pool interactively |

---

## 🧠 How It Works Under The Hood

Claude Code stores project sessions as local JSONL transcripts:
```
~/<config_dir>/projects/<CWD-encoded>/<session-id>.jsonl
```

When an account exhausts its tokens:
1. `claude-pool` detects the limit exit code or message.
2. Identifies the active `<session-id>` and working directory.
3. Copies `<session-id>.jsonl` and sidecar tool results into the next standby account's configuration directory.
4. Sets `CLAUDE_CONFIG_DIR = ~/.claude-account2`.
5. Relaunches `claude --resume <session-id>` with zero loss of memory.

---

## 🛠️ Troubleshooting & FAQ

### What happens if an account's login expires?
OAuth tokens occasionally expire. Run:
```bash
claude-pool check-auth
```
If an account is flagged as `EXPIRED`, simply re-authenticate it with:
```bash
claude-pool login <account_name>
```

### Can I pass custom Claude arguments?
Yes! Any arguments passed to `claude-pool` pass directly through to Claude Code:
```bash
claude-pool --model opus --verbose
claude-pool -p "Fix the failing tests in auth.py"
```

---

## 📄 License

Distributed under the [MIT License](LICENSE).
