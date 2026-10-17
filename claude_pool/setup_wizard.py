import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Optional, List
from claude_pool.models import Account
from claude_pool.config import ConfigManager
from claude_pool.pool import AccountPoolManager
from claude_pool.ui import (
    console,
    COLOR_PRIMARY,
    COLOR_SUCCESS,
    COLOR_WARNING,
    COLOR_ACCENT,
    COLOR_BORDER,
    render_priority_table,
)
from rich.panel import Panel
from rich.text import Text
from rich import box


def check_claude_cli_installed() -> bool:
    """Verify that the official Claude Code CLI is installed in PATH."""
    return shutil.which("claude") is not None


def run_account_login(config_dir: Path, email: Optional[str] = None) -> bool:
    """Spawn interactive browser login under the target configuration directory."""
    env = os.environ.copy()
    default_claude_path = str(Account("tmp", "~/.claude", 1).resolved_path)

    if str(config_dir.resolve()) != default_claude_path:
        env["CLAUDE_CONFIG_DIR"] = str(config_dir.resolve())
    else:
        env.pop("CLAUDE_CONFIG_DIR", None)

    # Clear any provider overrides
    for k in ["ANTHROPIC_BASE_URL", "ANTHROPIC_API_KEY", "ANTHROPIC_DEFAULT_SONNET_MODEL"]:
        env.pop(k, None)

    cmd = ["claude", "auth", "login"]
    if email:
        cmd.extend(["--email", email])

    try:
        console.print(f"[dim]Launching Claude OAuth login in your browser...[/dim]")
        proc = subprocess.run(cmd, env=env)
        return proc.returncode == 0
    except Exception as e:
        console.print(f"[bold #ef4444]Failed to launch claude auth login:[/] {e}")
        return False


def run_setup_wizard():
    """Interactive onboarding wizard for brand-new users setting up from scratch."""
    console.print()
    banner = Text()
    banner.append("Welcome to Claude Pool Setup Wizard\n", style=f"bold {COLOR_PRIMARY}")
    banner.append("Connect multiple Claude subscriptions into one unified token pool.\n", style="white")
    banner.append("Zero manual account switching · Automatic session failover · Live quota metrics", style=COLOR_ACCENT)

    console.print(
        Panel(
            banner,
            title=f"[{COLOR_PRIMARY}] claude-pool setup [/{COLOR_PRIMARY}]",
            title_align="left",
            border_style=COLOR_BORDER,
            box=box.ROUNDED,
            padding=(1, 2),
        )
    )
    console.print()

    # Step 1: Check prerequisites
    if not check_claude_cli_installed():
        console.print("[bold #ef4444]✗ Claude Code CLI was not found in your PATH.[/]")
        console.print("Please install Claude Code CLI first by running:\n")
        console.print("  [bold cyan]npm install -g @anthropic-ai/claude-code[/]\n")
        console.print("Once installed, run [bold cyan]claude-pool setup[/] again.")
        return

    console.print("[bold #10b981]✓ Claude Code CLI detected.[/]")

    cfg = ConfigManager()
    cfg.ensure_config_dir()
    existing_accounts = cfg.load_accounts()
    pool_mgr = AccountPoolManager(cfg)

    new_accounts: List[Account] = []

    # Step 2: Primary Account
    home = Path.home()
    primary_dir = home / ".claude"
    primary_dir.mkdir(parents=True, exist_ok=True)
    primary_acct = Account(name="primary", config_dir=str(primary_dir), priority=1)

    is_logged_in, email = pool_mgr.check_auth_status(primary_acct)

    if is_logged_in:
        console.print(f"\n[bold {COLOR_PRIMARY}]Account #1 (Primary):[/]")
        console.print(f"  ✓ Already authenticated as: [bold white]{email or 'Logged In'}[/]")
        primary_acct.email = email
        new_accounts.append(primary_acct)
    else:
        console.print(f"\n[bold {COLOR_PRIMARY}]Account #1 (Primary):[/]")
        console.print("  No active session found in ~/.claude.")
        do_login = input("  Would you like to log in to your Primary Claude account now? [Y/n]: ").strip().lower()
        if do_login in ("", "y", "yes"):
            target_email = input("  Enter email address (optional, press Enter to skip): ").strip() or None
            run_account_login(primary_dir, email=target_email)
            ok, detected_email = pool_mgr.check_auth_status(primary_acct)
            if ok:
                console.print(f"  [bold #10b981]✓ Primary account verified as: {detected_email}[/]")
                primary_acct.email = detected_email
            new_accounts.append(primary_acct)

    # Step 3: Add Secondary / Standby Accounts
    acct_counter = 2
    while True:
        console.print()
        add_more = input(f"Would you like to add another Claude subscription account? [y/N]: ").strip().lower()
        if add_more not in ("y", "yes"):
            break

        default_name = f"account{acct_counter}"
        name_input = input(f"  Enter account name [default: {default_name}]: ").strip()
        acct_name = name_input if name_input else default_name

        acct_dir = home / f".claude-{acct_name}"
        acct_dir.mkdir(parents=True, exist_ok=True)
        acct = Account(name=acct_name, config_dir=str(acct_dir), priority=acct_counter)

        # Check if already authenticated
        is_auth, email = pool_mgr.check_auth_status(acct)
        if is_auth and email:
            console.print(f"  ✓ Already authenticated as: [bold white]{email}[/]")
            acct.email = email
        else:
            console.print(f"  Opening browser to sign in for '{acct_name}'...")
            target_email = input("  Enter email address (optional, press Enter to skip): ").strip() or None
            run_account_login(acct_dir, email=target_email)
            ok, detected_email = pool_mgr.check_auth_status(acct)
            if ok:
                console.print(f"  [bold #10b981]✓ Account '{acct_name}' verified as: {detected_email}[/]")
                acct.email = detected_email
            else:
                console.print(f"  [#f59e0b]Note: Account '{acct_name}' registered. You can log in later with claude-pool login {acct_name}.[/]")

        new_accounts.append(acct)
        acct_counter += 1

    # Save accounts
    if new_accounts:
        cfg.save_accounts(new_accounts)
        console.print()
        console.print("[bold #10b981]✓ Setup complete! Your Claude Pool is configured:[/]")
        render_priority_table(new_accounts, active_name=new_accounts[0].name)
        console.print("To start your uninterrupted coding session, simply run:\n")
        console.print("  [bold cyan]claude-pool[/]\n")
    else:
        console.print("\n[#f59e0b]No accounts were added. You can run 'claude-pool setup' anytime.[/]\n")


def add_account_interactive(account_name: Optional[str] = None):
    """Interactively add and authenticate a single new account."""
    if not account_name:
        account_name = input("Enter new account name: ").strip()
    if not account_name:
        console.print("[bold #ef4444]Account name cannot be empty.[/]")
        return

    cfg = ConfigManager()
    accounts = cfg.load_accounts()

    if any(a.name.lower() == account_name.lower() for a in accounts):
        console.print(f"[bold #ef4444]Account '{account_name}' already exists in pool.[/]")
        return

    acct_dir = Path.home() / f".claude-{account_name}"
    acct_dir.mkdir(parents=True, exist_ok=True)
    next_prio = len(accounts) + 1

    acct = Account(name=account_name, config_dir=str(acct_dir), priority=next_prio)

    console.print(f"Opening browser login for account '{account_name}'...")
    email = input("Enter email address (optional, press Enter to skip): ").strip() or None
    run_account_login(acct_dir, email=email)

    pool_mgr = AccountPoolManager(cfg)
    ok, detected_email = pool_mgr.check_auth_status(acct)
    if ok:
        console.print(f"[bold #10b981]✓ Account '{account_name}' authenticated as: {detected_email}[/]")
        acct.email = detected_email

    accounts.append(acct)
    cfg.save_accounts(accounts)
    console.print(f"[bold #10b981]✓ Account '{account_name}' added as Priority {next_prio}.[/]")
