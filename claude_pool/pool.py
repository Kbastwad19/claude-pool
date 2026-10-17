import json
import os
import subprocess
import time
from typing import List, Optional, Tuple
from claude_pool.models import Account
from claude_pool.config import ConfigManager


class AccountPoolManager:
    """Manages the pool of Claude accounts, priority ordering, health, and failover."""

    def __init__(self, config_manager: Optional[ConfigManager] = None):
        self.config_manager = config_manager or ConfigManager()
        self.accounts: List[Account] = self.config_manager.load_accounts()

    def reload(self):
        self.accounts = self.config_manager.load_accounts()

    def check_auth_status(self, account: Account) -> Tuple[bool, Optional[str]]:
        """Run `claude auth status` under this account to verify validity and extract email."""
        env = os.environ.copy()
        if str(account.resolved_path) != str(Account(name="tmp", config_dir="~/.claude", priority=1).resolved_path):
            env["CLAUDE_CONFIG_DIR"] = str(account.resolved_path)
        else:
            env.pop("CLAUDE_CONFIG_DIR", None)

        try:
            res = subprocess.run(
                ["claude", "auth", "status"],
                env=env,
                capture_output=True,
                text=True,
                timeout=10,
            )
            if res.returncode == 0:
                try:
                    data = json.loads(res.stdout)
                    account.email = data.get("email")
                    account.org_name = data.get("orgName")
                    account.subscription_type = data.get("subscriptionType")
                    account.auth_valid = data.get("loggedIn", True)
                    return account.auth_valid, account.email
                except Exception:
                    account.auth_valid = True
                    return True, None
            else:
                account.auth_valid = False
                return False, res.stderr.strip()
        except Exception as e:
            account.auth_valid = False
            return False, str(e)

    def verify_all_accounts(self):
        """Check and update auth status for all registered accounts."""
        for a in self.accounts:
            self.check_auth_status(a)
        self.config_manager.save_accounts(self.accounts)

    def get_active_account(self) -> Optional[Account]:
        """Returns the highest priority ready account (lowest priority number)."""
        # Ensure sorted by priority
        ready = [a for a in sorted(self.accounts, key=lambda x: x.priority) if a.is_ready]
        return ready[0] if ready else None

    def get_standby_accounts(self, current: Optional[Account] = None) -> List[Account]:
        """Returns ready accounts other than current, in priority order."""
        ready = [
            a for a in sorted(self.accounts, key=lambda x: x.priority)
            if a.is_ready and (current is None or a.name != current.name)
        ]
        return ready

    def mark_rate_limited(self, account: Account, cooldown_seconds: int = 3600):
        account.rate_limited_until = time.time() + cooldown_seconds
        self.config_manager.save_accounts(self.accounts)

    def mark_auth_expired(self, account: Account):
        account.auth_valid = False
        self.config_manager.save_accounts(self.accounts)

    def set_priority(self, account_name: str, priority: int) -> bool:
        ok = self.config_manager.update_account_priority(account_name, priority)
        if ok:
            self.reload()
        return ok

    def reorder_priorities(self, account_names: List[str]) -> bool:
        ok = self.config_manager.reorder_priorities(account_names)
        if ok:
            self.reload()
        return ok
