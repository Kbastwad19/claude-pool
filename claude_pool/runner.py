import os
import subprocess
import sys
import time
from typing import List, Optional
from pathlib import Path
from claude_pool.models import Account
from claude_pool.pool import AccountPoolManager
from claude_pool.session_sync import SessionSyncEngine
from claude_pool.metrics import MetricsEngine
from claude_pool.detector import OutputDetector
from claude_pool.ui import render_session_header, render_failover_banner, console


class ProcessRunner:
    """Spawns Claude CLI with account isolation, handles failover & session transfer."""

    def __init__(self, pool_manager: AccountPoolManager):
        self.pool_manager = pool_manager

    def clean_env_for_account(self, account: Account) -> dict:
        """Prepare clean environment matching account's config directory."""
        env = os.environ.copy()

        # Set CLAUDE_CONFIG_DIR if not the default ~/.claude
        default_claude_path = str(Account("tmp", "~/.claude", 1).resolved_path)
        if str(account.resolved_path) != default_claude_path:
            env["CLAUDE_CONFIG_DIR"] = str(account.resolved_path)
        else:
            env.pop("CLAUDE_CONFIG_DIR", None)

        # Clear any overrides from third-party profiles (Groq, Bedrock)
        for key in [
            "ANTHROPIC_BASE_URL",
            "ANTHROPIC_API_KEY",
            "ANTHROPIC_DEFAULT_SONNET_MODEL",
            "CLAUDE_CODE_USE_BEDROCK",
            "AWS_PROFILE",
            "AWS_REGION",
            "ANTHROPIC_DEFAULT_OPUS_MODEL",
        ]:
            env.pop(key, None)

        return env

    def run_session(self, extra_args: Optional[List[str]] = None, initial_account_name: Optional[str] = None):
        """
        Runs Claude session on active account. If a rate limit is hit,
        automatically syncs session and resumes on the next priority account.
        """
        extra_args = list(extra_args or [])

        # 1. Determine starting account
        active_account: Optional[Account] = None
        if initial_account_name:
            active_account = next(
                (a for a in self.pool_manager.accounts if a.name.lower() == initial_account_name.lower()),
                None,
            )

        if not active_account:
            active_account = self.pool_manager.get_active_account()

        if not active_account:
            console.print("[bold #ef4444]No ready accounts found in Claude Pool![/]")
            console.print("Run [bold cyan]claude-pool status[/] or [bold cyan]claude-pool check-auth[/] to diagnose.")
            return

        resume_session_id: Optional[str] = None

        # Check if user already passed --resume or -r
        for idx, arg in enumerate(extra_args):
            if arg in ("-r", "--resume") and idx + 1 < len(extra_args):
                resume_session_id = extra_args[idx + 1]

        while active_account:
            standby = self.pool_manager.get_standby_accounts(current=active_account)
            pool_stats = MetricsEngine.get_pool_stats(self.pool_manager.accounts)

            # Display elegant session header HUD
            render_session_header(active_account, standby, pool_stats)

            # Build command
            cmd = ["claude"] + list(extra_args)
            if resume_session_id and "-r" not in cmd and "--resume" not in cmd:
                cmd.extend(["--resume", resume_session_id])

            env = self.clean_env_for_account(active_account)

            # Record session start time to help identify newest session file
            session_start = time.time()

            try:
                # Interactive execution - full terminal passthrough
                proc = subprocess.run(cmd, env=env)
                exit_code = proc.returncode
            except KeyboardInterrupt:
                console.print("\n[dim]Session ended by user.[/dim]")
                break
            except Exception as e:
                console.print(f"[bold #ef4444]Error launching claude:[/] {e}")
                break

            # Check if user exited normally (exit code 0)
            if exit_code == 0:
                console.print("\n[#10b981]✓ Claude session finished normally.[/#10b981]")
                break

            # If exit code was non-zero, check if a rate limit or exhaustion occurred
            latest_id = SessionSyncEngine.get_latest_session_id(active_account)
            if latest_id:
                resume_session_id = latest_id

            # Verify if account hit rate limit by checking recent project logs or error
            # Or mark rate-limited and failover if standby accounts exist
            if standby:
                next_account = standby[0]
                self.pool_manager.mark_rate_limited(active_account)

                # Transfer session to next account
                transferred_id = None
                if resume_session_id:
                    transferred_id = SessionSyncEngine.transfer_session(
                        source_account=active_account,
                        target_account=next_account,
                        session_id=resume_session_id,
                    )

                render_failover_banner(active_account, next_account, transferred_id or resume_session_id)
                active_account = next_account
                if transferred_id:
                    resume_session_id = transferred_id
                time.sleep(1)
            else:
                console.print("\n[bold #f59e0b]⚠️ All accounts in pool are currently exhausted or unavailable.[/]")
                break
