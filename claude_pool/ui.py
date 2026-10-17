import sys
import shutil
from typing import List, Optional, Dict
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich import box
from claude_pool.models import Account, PoolStats, AccountStats, ModelUsage, QuotaInfo
from claude_pool.metrics import format_token_count

# Ensure UTF-8 output on Windows consoles
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

console = Console()

# Refined aesthetic palette (Linear / Raycast inspired)
COLOR_PRIMARY = "#818cf8"     # Soft Indigo
COLOR_ACCENT = "#f97316"      # Warm Terracotta
COLOR_SUCCESS = "#10b981"     # Mint Emerald
COLOR_WARNING = "#f59e0b"     # Warm Amber
COLOR_MUTED = "#64748b"       # Soft Slate
COLOR_BORDER = "#334155"      # Dark Slate


def make_pill(status: str) -> Text:
    """Generate aesthetic status pill."""
    if status == "active":
        return Text(" ACTIVE ", style=f"bold white on {COLOR_SUCCESS}")
    elif status == "standby":
        return Text(" STANDBY ", style=f"bold white on {COLOR_MUTED}")
    elif status == "rate_limited":
        return Text(" COOLDOWN ", style=f"bold black on {COLOR_WARNING}")
    elif status == "auth_expired":
        return Text(" EXPIRED ", style="bold white on #ef4444")
    return Text(f" {status.upper()} ", style="dim")


def make_gauge(pct_remaining: Optional[int], width: int = 10) -> Text:
    """Generate visual progress gauge like [███████░░░] 71%."""
    if pct_remaining is None:
        return Text("—", style="dim")

    pct = max(0, min(100, pct_remaining))
    filled_len = int(round((pct / 100) * width))
    empty_len = width - filled_len

    if pct > 40:
        bar_color = COLOR_SUCCESS
    elif pct > 15:
        bar_color = COLOR_WARNING
    else:
        bar_color = "#ef4444"

    res = Text()
    res.append("█" * filled_len, style=f"bold {bar_color}")
    res.append("░" * empty_len, style=COLOR_BORDER)
    res.append(f" {pct}%", style=f"bold {bar_color}")
    return res


def render_session_header(
    active_account: Account,
    standby_accounts: List[Account],
    pool_stats: Optional[PoolStats] = None,
):
    """Clean, minimalist HUD bar anchored before launching session."""
    standby_names = ", ".join([a.name for a in standby_accounts]) if standby_accounts else "none"
    today_pool_str = format_token_count(pool_stats.today_pool_tokens) if pool_stats else "0"

    content = Text()
    content.append("  Active Account   ", style=f"bold {COLOR_PRIMARY}")
    content.append(f"{active_account.name} ", style="bold white")
    content.append(f"[Priority {active_account.priority}]", style=f"bold {COLOR_ACCENT}")

    # If quota info is available, append remaining %
    if active_account.quota and active_account.quota.session_remaining_pct is not None:
        rem = active_account.quota.session_remaining_pct
        content.append(f" · {rem}% remaining", style=f"bold {COLOR_SUCCESS if rem > 30 else COLOR_WARNING}")
        if active_account.quota.session_reset:
            content.append(f" (resets {active_account.quota.session_reset})", style=COLOR_MUTED)
    elif active_account.email:
        content.append(f" · {active_account.email}", style=COLOR_MUTED)
    content.append("\n")

    content.append("  Pool Today       ", style=f"bold {COLOR_PRIMARY}")
    content.append(f"{today_pool_str} tokens", style="bold white")
    content.append(f" across {len(standby_accounts) + 1} accounts", style=f"{COLOR_MUTED}")
    content.append("\n")

    content.append("  Standby Queue    ", style=f"bold {COLOR_PRIMARY}")
    content.append(standby_names, style="white")

    panel = Panel(
        content,
        title=f"[{COLOR_PRIMARY}] claude-pool [/{COLOR_PRIMARY}]",
        title_align="left",
        border_style=COLOR_BORDER,
        box=box.ROUNDED,
        padding=(0, 1),
    )
    console.print()
    console.print(panel)
    console.print()


def render_failover_banner(
    old_account: Account,
    new_account: Account,
    session_id: Optional[str] = None,
):
    """Elegant transition card displayed during auto-switch."""
    content = Text()
    content.append("Rate limit reached on ", style=f"bold {COLOR_WARNING}")
    content.append(f"{old_account.name}\n\n", style="bold white")

    if session_id:
        content.append("  + Preserved active session: ", style=COLOR_SUCCESS)
        content.append(f"{session_id[:12]}...\n", style="white")
    content.append("  + Synchronized project state to ", style=COLOR_SUCCESS)
    content.append(f"{new_account.name}\n", style="white")
    content.append("  -> Continuing on ", style=f"bold {COLOR_PRIMARY}")
    content.append(f"{new_account.name} (Priority {new_account.priority})\n", style="bold white")

    panel = Panel(
        content,
        title=f"[{COLOR_ACCENT}] Auto-Failover Transition [/{COLOR_ACCENT}]",
        title_align="left",
        border_style=COLOR_ACCENT,
        box=box.ROUNDED,
        padding=(1, 2),
    )
    console.print()
    console.print(panel)
    console.print()


def render_priority_table(accounts: List[Account], active_name: Optional[str] = None):
    """Aesthetic table showing account priority order and health."""
    table = Table(
        box=box.ROUNDED,
        border_style=COLOR_BORDER,
        header_style=f"bold {COLOR_PRIMARY}",
        expand=False,
    )

    table.add_column("Rank", justify="center", style="bold")
    table.add_column("Priority", justify="center")
    table.add_column("Account", style="bold white")
    table.add_column("Status", justify="center")
    table.add_column("Email", style=COLOR_MUTED)
    table.add_column("Plan", style=COLOR_MUTED)
    table.add_column("Config Directory", style="dim")

    for idx, a in enumerate(sorted(accounts, key=lambda x: x.priority), start=1):
        if a.is_rate_limited:
            st = "rate_limited"
        elif a.auth_valid is False:
            st = "auth_expired"
        elif active_name and a.name == active_name:
            st = "active"
        else:
            st = "standby"

        rank_badge = "#1" if idx == 1 else f"#{idx}"
        prio_text = f"P{a.priority}"
        email_text = a.email or "-"
        plan_text = a.subscription_type or "-"

        table.add_row(
            rank_badge,
            prio_text,
            a.name,
            make_pill(st),
            email_text,
            plan_text,
            a.config_dir,
        )

    console.print()
    console.print(table)
    console.print()


def render_limits_table(accounts: List[Account]):
    """Clean table showing remaining quota % and reset countdowns across pool."""
    console.print()
    table = Table(
        title=f"[{COLOR_PRIMARY}]Pool Quota & Remaining Usage[/{COLOR_PRIMARY}]",
        title_justify="left",
        box=box.ROUNDED,
        border_style=COLOR_BORDER,
        header_style=f"bold {COLOR_PRIMARY}",
        expand=False,
    )

    table.add_column("Rank", justify="center", style="bold")
    table.add_column("Priority", justify="center")
    table.add_column("Account", style="bold white")
    table.add_column("Status", justify="center")
    table.add_column("Session Remaining")
    table.add_column("Session Resets At")
    table.add_column("Weekly Remaining")
    table.add_column("Weekly Resets At")

    for idx, a in enumerate(sorted(accounts, key=lambda x: x.priority), start=1):
        if a.is_rate_limited:
            st = "rate_limited"
        elif a.auth_valid is False:
            st = "auth_expired"
        else:
            st = "active" if idx == 1 else "standby"

        rank_badge = "#1" if idx == 1 else f"#{idx}"
        prio_label = f"P{a.priority}"

        if a.quota:
            s_gauge = make_gauge(a.quota.session_remaining_pct)
            s_reset = a.quota.session_reset or "-"
            w_gauge = make_gauge(a.quota.week_remaining_pct)
            w_reset = a.quota.week_reset or "-"
        else:
            s_gauge = Text("-", style="dim")
            s_reset = "-"
            w_gauge = Text("-", style="dim")
            w_reset = "-"

        table.add_row(
            rank_badge,
            prio_label,
            a.name,
            make_pill(st),
            s_gauge,
            s_reset,
            w_gauge,
            w_reset,
        )

    console.print(table)
    console.print()


def render_dashboard(accounts: List[Account], pool_stats: PoolStats, active_name: Optional[str] = None):
    """Sleek token pool dashboard with proportional gauges and category breakdown."""
    console.print()

    # 1. Header summary banner with category totals
    summary_text = Text()
    summary_text.append("Today's Pool Total: ", style=COLOR_MUTED)
    summary_text.append(f"{format_token_count(pool_stats.today_pool_tokens)}   ", style=f"bold {COLOR_SUCCESS}")
    summary_text.append("│ Output: ", style=COLOR_MUTED)
    summary_text.append(f"{format_token_count(pool_stats.today_pool_output)}   ", style=f"bold {COLOR_ACCENT}")
    summary_text.append("│ Cache: ", style=COLOR_MUTED)
    summary_text.append(f"{format_token_count(pool_stats.today_pool_cache)}   ", style=f"bold {COLOR_PRIMARY}")
    summary_text.append("│ Lifetime Total: ", style=COLOR_MUTED)
    summary_text.append(f"{format_token_count(pool_stats.lifetime_pool_cache + pool_stats.lifetime_pool_output)}", style="bold white")

    console.print(
        Panel(
            summary_text,
            title=f"[{COLOR_PRIMARY}] Token Pool Dashboard [/{COLOR_PRIMARY}]",
            title_align="left",
            border_style=COLOR_BORDER,
            box=box.ROUNDED,
        )
    )

    # 2. Account token breakdown table
    table = Table(
        box=box.ROUNDED,
        border_style=COLOR_BORDER,
        header_style=f"bold {COLOR_PRIMARY}",
        expand=True,
    )

    table.add_column("Priority", justify="center", width=8)
    table.add_column("Account", style="bold white", width=14)
    table.add_column("Status", justify="center", width=14)
    table.add_column("Remaining Quota", width=20)
    table.add_column("Today's Tokens", justify="right", width=16)
    table.add_column("Model Breakdown (Today)", width=28)
    table.add_column("Sessions", justify="center", width=10)

    acct_map = {a.name: a for a in accounts}

    for stat in sorted(pool_stats.accounts, key=lambda s: acct_map.get(s.account_name, Account("","",99)).priority):
        acct = acct_map.get(stat.account_name)
        if not acct:
            continue

        if acct.is_rate_limited:
            st = "rate_limited"
        elif acct.auth_valid is False:
            st = "auth_expired"
        elif active_name and acct.name == active_name:
            st = "active"
        else:
            st = "standby"

        prio_label = f"P{acct.priority}"
        today_formatted = format_token_count(stat.today_total_tokens)

        # Quota gauge
        if acct.quota and acct.quota.session_remaining_pct is not None:
            rem_gauge = make_gauge(acct.quota.session_remaining_pct, width=8)
        else:
            rem_gauge = Text("—", style="dim")

        # Model breakdown string
        breakdown = []
        for m_name, m_tokens in stat.today_tokens_by_model.items():
            short_model = m_name.replace("claude-", "")
            breakdown.append(f"{short_model}: {format_token_count(m_tokens)}")
        breakdown_str = " · ".join(breakdown) if breakdown else "-"

        table.add_row(
            prio_label,
            acct.name,
            make_pill(st),
            rem_gauge,
            f"[bold white]{today_formatted}[/]",
            f"[{COLOR_MUTED}]{breakdown_str}[/]",
            str(stat.total_sessions),
        )

    console.print(table)
    console.print(f"[dim]Tip: Run [bold cyan]claude-pool limits[/] to inspect reset countdowns & weekly quotas.[/dim]\n")


def render_account_breakdown(account: Account, stats: AccountStats):
    """Detailed breakdown view for a single account showing Input/Output/Cache per model."""
    console.print()

    # Header Card
    header_text = Text()
    header_text.append(f"Account: {account.name} ", style="bold white")
    header_text.append(f"[Priority {account.priority}]", style=f"bold {COLOR_ACCENT}")
    if account.quota and account.quota.session_remaining_pct is not None:
        header_text.append(f" · {account.quota.session_remaining_pct}% session quota left", style=f"bold {COLOR_SUCCESS}")
    if account.email:
        header_text.append(f" · {account.email}", style=COLOR_MUTED)
    header_text.append(f"\nConfig Directory: {account.config_dir}", style="dim")

    console.print(
        Panel(
            header_text,
            title=f"[{COLOR_PRIMARY}] Token Breakdown: {account.name} [/{COLOR_PRIMARY}]",
            title_align="left",
            border_style=COLOR_BORDER,
            box=box.ROUNDED,
        )
    )

    # Today's Token Breakdown Table
    t_today = Table(
        title=f"[{COLOR_SUCCESS}]Today's Usage (Total: {format_token_count(stats.today_total_tokens)})[/{COLOR_SUCCESS}]",
        title_justify="left",
        box=box.ROUNDED,
        border_style=COLOR_BORDER,
        header_style=f"bold {COLOR_PRIMARY}",
        expand=True,
    )

    t_today.add_column("Model", style="bold white", width=22)
    t_today.add_column("Input Tokens", justify="right", style=COLOR_MUTED)
    t_today.add_column("Output Tokens", justify="right", style=COLOR_ACCENT)
    t_today.add_column("Cache Read", justify="right", style=COLOR_PRIMARY)
    t_today.add_column("Cache Create", justify="right", style=COLOR_MUTED)
    t_today.add_column("Total Tokens", justify="right", style="bold white")

    if stats.today_models_detail:
        for model_name, m_usage in stats.today_models_detail.items():
            t_today.add_row(
                model_name,
                f"{m_usage.input_tokens:,}",
                f"{m_usage.output_tokens:,}",
                f"{m_usage.cache_read_tokens:,}",
                f"{m_usage.cache_creation_tokens:,}",
                f"{m_usage.total_tokens:,} ({format_token_count(m_usage.total_tokens)})",
            )
        # Total Row
        total_cache = stats.today_cache_read_tokens + stats.today_cache_creation_tokens
        t_today.add_row(
            "[bold]All Models[/bold]",
            f"[bold]{stats.today_input_tokens:,}[/bold]",
            f"[bold]{stats.today_output_tokens:,}[/bold]",
            f"[bold]{stats.today_cache_read_tokens:,}[/bold]",
            f"[bold]{stats.today_cache_creation_tokens:,}[/bold]",
            f"[bold]{stats.today_total_tokens:,} ({format_token_count(stats.today_total_tokens)})[/bold]",
        )
    else:
        t_today.add_row("No activity today", "-", "-", "-", "-", "0")

    console.print(t_today)
    console.print()

    # Lifetime Token Breakdown Table
    if stats.lifetime_models:
        t_life = Table(
            title=f"[{COLOR_PRIMARY}]Lifetime Usage (Sessions: {stats.total_sessions})[/{COLOR_PRIMARY}]",
            title_justify="left",
            box=box.ROUNDED,
            border_style=COLOR_BORDER,
            header_style=f"bold {COLOR_PRIMARY}",
            expand=True,
        )

        t_life.add_column("Model", style="bold white", width=22)
        t_life.add_column("Input Tokens", justify="right", style=COLOR_MUTED)
        t_life.add_column("Output Tokens", justify="right", style=COLOR_ACCENT)
        t_life.add_column("Cache Read", justify="right", style=COLOR_PRIMARY)
        t_life.add_column("Cache Create", justify="right", style=COLOR_MUTED)
        t_life.add_column("Total Tokens", justify="right", style="bold white")

        for model_name, m_usage in stats.lifetime_models.items():
            t_life.add_row(
                model_name,
                f"{m_usage.input_tokens:,}",
                f"{m_usage.output_tokens:,}",
                f"{m_usage.cache_read_tokens:,}",
                f"{m_usage.cache_creation_tokens:,}",
                f"{m_usage.total_tokens:,} ({format_token_count(m_usage.total_tokens)})",
            )
        console.print(t_life)
        console.print()
