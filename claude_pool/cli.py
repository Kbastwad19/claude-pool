import sys
import click
from pathlib import Path
from typing import List, Optional
from claude_pool.config import ConfigManager
from claude_pool.pool import AccountPoolManager
from claude_pool.metrics import MetricsEngine
from claude_pool.quota import QuotaEngine
from claude_pool.runner import ProcessRunner
from claude_pool.setup_wizard import run_setup_wizard, add_account_interactive, run_account_login
from claude_pool.ui import (
    render_priority_table,
    render_dashboard,
    render_account_breakdown,
    render_limits_table,
    console,
    COLOR_PRIMARY,
    COLOR_SUCCESS,
    COLOR_WARNING,
)

KNOWN_COMMANDS = {
    "start",
    "setup",
    "dashboard",
    "limits",
    "remaining",
    "quota",
    "usage",
    "tokens",
    "priority",
    "set-priority",
    "status",
    "accounts",
    "check-auth",
    "login",
    "add",
    "--help",
    "-h",
}


@click.group(invoke_without_command=True)
@click.pass_context
@click.option("--account", "-a", default=None, help="Force start with specific account name")
def cli(ctx, account):
    """Claude Pool: Multi-account token pooling and seamless failover manager."""
    if ctx.invoked_subcommand is None:
        mgr = AccountPoolManager()
        # Fast load cached quota if available
        QuotaEngine.fetch_all_quotas(mgr.accounts, force_refresh=False)
        runner = ProcessRunner(mgr)
        runner.run_session(extra_args=[], initial_account_name=account)


@cli.command(name="setup")
def setup_cmd():
    """Run the guided setup wizard to connect multiple Claude subscriptions from scratch."""
    run_setup_wizard()


@cli.command(name="start", context_settings=dict(ignore_unknown_options=True, allow_extra_args=True))
@click.option("--account", "-a", default=None, help="Force start with specific account name")
@click.pass_context
def start_cmd(ctx, account):
    """Launch interactive Claude session with pooled accounts and auto-failover."""
    mgr = AccountPoolManager()
    QuotaEngine.fetch_all_quotas(mgr.accounts, force_refresh=False)
    runner = ProcessRunner(mgr)
    runner.run_session(extra_args=ctx.args, initial_account_name=account)


@cli.command(name="limits")
@click.option("--refresh", "-r", is_flag=True, help="Force live query from Claude servers")
def limits_cmd(refresh: bool):
    """Inspect exact % quota remaining and reset countdowns across all accounts."""
    mgr = AccountPoolManager()
    with console.status("[bold #818cf8]Querying live Claude usage quotas & reset countdowns...[/]"):
        QuotaEngine.fetch_all_quotas(mgr.accounts, force_refresh=refresh)
    render_limits_table(mgr.accounts)


@cli.command(name="remaining")
@click.option("--refresh", "-r", is_flag=True, help="Force live query from Claude servers")
def remaining_cmd(refresh: bool):
    """Alias for 'limits': view remaining quota % and reset countdowns."""
    limits_cmd.callback(refresh)


@cli.command(name="quota")
@click.option("--refresh", "-r", is_flag=True, help="Force live query from Claude servers")
def quota_cmd(refresh: bool):
    """Alias for 'limits': view remaining quota % and reset countdowns."""
    limits_cmd.callback(refresh)


@cli.command(name="dashboard")
@click.option("--refresh", "-r", is_flag=True, help="Force refresh quota data")
def dashboard_cmd(refresh: bool):
    """Display real-time aggregated token metrics across all Claude accounts."""
    mgr = AccountPoolManager()
    QuotaEngine.fetch_all_quotas(mgr.accounts, force_refresh=refresh)
    stats = MetricsEngine.get_pool_stats(mgr.accounts)
    active = mgr.get_active_account()
    render_dashboard(mgr.accounts, stats, active_name=active.name if active else None)


@cli.command(name="usage")
@click.argument("account_name", required=False, default=None)
def usage_cmd(account_name: Optional[str]):
    """View deep token breakdown (Input, Output, Cache Read/Create) by account."""
    mgr = AccountPoolManager()
    QuotaEngine.fetch_all_quotas(mgr.accounts, force_refresh=False)
    if account_name:
        target = next((a for a in mgr.accounts if a.name.lower() == account_name.lower()), None)
        if not target:
            console.print(f"[bold #ef4444]Account '{account_name}' not found in pool.[/]")
            return
        stat = MetricsEngine.read_account_stats(target)
        render_account_breakdown(target, stat)
    else:
        for acct in mgr.accounts:
            stat = MetricsEngine.read_account_stats(acct)
            render_account_breakdown(acct, stat)


@cli.command(name="tokens")
@click.argument("account_name", required=False, default=None)
def tokens_cmd(account_name: Optional[str]):
    """Alias for 'usage': view token breakdown by account."""
    usage_cmd.callback(account_name)


@cli.command(name="priority")
@click.option("--set", "set_target", nargs=2, type=(str, int), help="Set priority: --set <account> <priority>")
@click.option("--order", help="Reorder accounts by comma-separated names, e.g. primary,account4,account2")
def priority_cmd(set_target, order):
    """View or update the priority order of accounts."""
    mgr = AccountPoolManager()

    if set_target:
        name, prio = set_target
        if mgr.set_priority(name, prio):
            console.print(f"[{COLOR_SUCCESS}]✓ Priority updated for {name} -> P{prio}[/]")
        else:
            console.print(f"[bold #ef4444]Account '{name}' not found.[/]")
            return

    if order:
        names = [n.strip() for n in order.split(",") if n.strip()]
        if mgr.reorder_priorities(names):
            console.print(f"[{COLOR_SUCCESS}]✓ Priority order updated: {', '.join(names)}[/]")
        else:
            console.print("[bold #ef4444]Failed to reorder accounts.[/]")
            return

    active = mgr.get_active_account()
    render_priority_table(mgr.accounts, active_name=active.name if active else None)


@cli.command(name="set-priority")
@click.argument("account_name")
@click.argument("priority_val", type=int)
def set_priority_cmd(account_name: str, priority_val: int):
    """Set the priority level for an account (e.g. claude-pool set-priority primary 1)."""
    mgr = AccountPoolManager()
    if mgr.set_priority(account_name, priority_val):
        console.print(f"[{COLOR_SUCCESS}]✓ Priority for '{account_name}' set to P{priority_val}[/]")
        active = mgr.get_active_account()
        render_priority_table(mgr.accounts, active_name=active.name if active else None)
    else:
        console.print(f"[bold #ef4444]Error: Account '{account_name}' not found in pool.[/]")


@cli.command(name="status")
def status_cmd():
    """Display account pool status, priority, and health overview."""
    mgr = AccountPoolManager()
    active = mgr.get_active_account()
    render_priority_table(mgr.accounts, active_name=active.name if active else None)


@cli.command(name="accounts")
def accounts_cmd():
    """List all configured accounts and their paths."""
    mgr = AccountPoolManager()
    active = mgr.get_active_account()
    render_priority_table(mgr.accounts, active_name=active.name if active else None)


@cli.command(name="check-auth")
def check_auth_cmd():
    """Verify live authentication status across all account directories."""
    mgr = AccountPoolManager()
    console.print(f"[{COLOR_PRIMARY}]Checking live authentication status across all accounts...[/{COLOR_PRIMARY}]")
    with console.status("Querying Claude auth endpoints..."):
        mgr.verify_all_accounts()

    active = mgr.get_active_account()
    render_priority_table(mgr.accounts, active_name=active.name if active else None)


@cli.command(name="login")
@click.argument("account_name")
@click.option("--email", help="Pre-populate login email")
def login_cmd(account_name: str, email: Optional[str]):
    """Re-authenticate or sign into an account in the pool."""
    cfg = ConfigManager()
    accounts = cfg.load_accounts()
    target = next((a for a in accounts if a.name.lower() == account_name.lower()), None)
    if not target:
        console.print(f"[bold #ef4444]Account '{account_name}' not found in pool.[/]")
        return

    console.print(f"Opening browser login for '{target.name}'...")
    run_account_login(target.resolved_path, email=email or target.email)
    pool_mgr = AccountPoolManager(cfg)
    ok, detected_email = pool_mgr.check_auth_status(target)
    if ok:
        console.print(f"[bold #10b981]✓ Account '{target.name}' verified as: {detected_email}[/]")
        target.email = detected_email
        target.auth_valid = True
        cfg.save_accounts(accounts)
    else:
        console.print(f"[bold #ef4444]Login verification failed for '{target.name}'.[/]")


@cli.command(name="add")
@click.argument("account_name", required=False, default=None)
@click.option("--dir", "config_dir", default=None, help="Custom configuration directory path")
@click.option("--priority", "-p", default=None, type=int, help="Priority level")
def add_cmd(account_name: Optional[str], config_dir: Optional[str], priority: Optional[int]):
    """Add a new account to the pool (interactive by default)."""
    if not config_dir:
        add_account_interactive(account_name)
        return

    # Non-interactive manual addition
    if not account_name:
        console.print("[bold #ef4444]Account name is required when specifying --dir.[/]")
        return

    cfg = ConfigManager()
    accounts = cfg.load_accounts()
    if any(a.name.lower() == account_name.lower() for a in accounts):
        console.print(f"[bold #ef4444]Account '{account_name}' already exists.[/]")
        return

    from claude_pool.models import Account
    prio_val = priority if priority is not None else len(accounts) + 1
    accounts.append(Account(name=account_name, config_dir=config_dir, priority=prio_val))
    cfg.save_accounts(accounts)
    console.print(f"[{COLOR_SUCCESS}]✓ Account '{account_name}' added to pool.[/{COLOR_SUCCESS}]")


def main():
    args = sys.argv[1:]
    if not args:
        cli()
        return

    if args[0] in KNOWN_COMMANDS:
        cli()
        return

    if args[0] in ("-a", "--account"):
        if len(args) > 2 and args[2] in KNOWN_COMMANDS:
            cli()
            return

    sys.argv.insert(1, "start")
    cli()


if __name__ == "__main__":
    main()
