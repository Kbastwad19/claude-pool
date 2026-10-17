import json
import os
import re
import subprocess
import time
from pathlib import Path
from typing import Dict, Optional, List
from claude_pool.models import Account, QuotaInfo


CACHE_FILE = Path.home() / ".claude-pool" / "quota_cache.json"


class QuotaEngine:
    """Queries live Claude Code /usage to retrieve exact % remaining and reset timers."""

    @classmethod
    def load_cache(cls) -> Dict[str, dict]:
        if not CACHE_FILE.exists():
            return {}
        try:
            return json.loads(CACHE_FILE.read_text(encoding="utf-8"))
        except Exception:
            return {}

    @classmethod
    def save_cache(cls, cache_data: Dict[str, dict]):
        try:
            CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
            CACHE_FILE.write_text(json.dumps(cache_data, indent=2), encoding="utf-8")
        except Exception:
            pass

    @classmethod
    def fetch_account_quota(cls, account: Account, force_refresh: bool = False) -> Optional[QuotaInfo]:
        cache = cls.load_cache()
        cached_entry = cache.get(account.name)

        if not force_refresh and cached_entry:
            q = QuotaInfo(
                session_used_pct=cached_entry.get("session_used_pct"),
                session_remaining_pct=cached_entry.get("session_remaining_pct"),
                session_reset=cached_entry.get("session_reset"),
                week_used_pct=cached_entry.get("week_used_pct"),
                week_remaining_pct=cached_entry.get("week_remaining_pct"),
                week_reset=cached_entry.get("week_reset"),
                last_checked=cached_entry.get("last_checked"),
            )
            if q.is_fresh:
                account.quota = q
                return q

        # Run `claude -p "/usage"` under this account's configuration directory
        env = os.environ.copy()
        default_claude_path = str(Account("tmp", "~/.claude", 1).resolved_path)
        if str(account.resolved_path) != default_claude_path:
            env["CLAUDE_CONFIG_DIR"] = str(account.resolved_path)
        else:
            env.pop("CLAUDE_CONFIG_DIR", None)

        # Clear any overrides
        for k in ["ANTHROPIC_BASE_URL", "ANTHROPIC_API_KEY", "ANTHROPIC_DEFAULT_SONNET_MODEL"]:
            env.pop(k, None)

        try:
            res = subprocess.run(
                ["claude", "-p", "/usage"],
                input="",
                env=env,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=15,
            )
            output = (res.stdout or "") + "\n" + (res.stderr or "")
        except Exception:
            return None

        q_info = QuotaInfo(last_checked=time.time())

        # Robust regex matching independent of character encoding
        m_session = re.search(r"Current session:\s*(\d+)%.*?resets\s*([^(\n\r]+)", output, re.IGNORECASE)
        if m_session:
            used = int(m_session.group(1))
            q_info.session_used_pct = used
            q_info.session_remaining_pct = max(0, 100 - used)
            q_info.session_reset = m_session.group(2).strip()

        m_week = re.search(r"Current week.*?:\s*(\d+)%.*?resets\s*([^(\n\r]+)", output, re.IGNORECASE)
        if m_week:
            used = int(m_week.group(1))
            q_info.week_used_pct = used
            q_info.week_remaining_pct = max(0, 100 - used)
            q_info.week_reset = m_week.group(2).strip()

        if q_info.session_used_pct is not None or q_info.week_used_pct is not None:
            account.quota = q_info
            cache[account.name] = {
                "session_used_pct": q_info.session_used_pct,
                "session_remaining_pct": q_info.session_remaining_pct,
                "session_reset": q_info.session_reset,
                "week_used_pct": q_info.week_used_pct,
                "week_remaining_pct": q_info.week_remaining_pct,
                "week_reset": q_info.week_reset,
                "last_checked": q_info.last_checked,
            }
            cls.save_cache(cache)
            return q_info

        return None

    @classmethod
    def fetch_all_quotas(cls, accounts: List[Account], force_refresh: bool = False):
        """Fetch quotas for all accounts (skips known expired accounts)."""
        for a in accounts:
            if a.auth_valid is False:
                continue
            cls.fetch_account_quota(a, force_refresh=force_refresh)
