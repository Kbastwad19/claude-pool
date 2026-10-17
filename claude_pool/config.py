import json
import os
from pathlib import Path
from typing import List, Dict, Any, Optional
from claude_pool.models import Account


DEFAULT_CONFIG_DIR = Path.home() / ".claude-pool"
CONFIG_FILE = DEFAULT_CONFIG_DIR / "config.json"


def get_default_accounts() -> List[Account]:
    """Auto-detect accounts based on common and existing config directories."""
    detected: List[Account] = []
    home = Path.home()

    candidates = [
        ("primary", home / ".claude", 1),
        ("account4", home / ".claude-account4", 2),
        ("account2", home / ".claude-account2", 3),
        ("bedrock", home / ".claude-bedrock", 4),
    ]

    for name, path, prio in candidates:
        if path.exists():
            detected.append(
                Account(
                    name=name,
                    config_dir=str(path),
                    priority=prio,
                    enabled=True,
                )
            )

    if not detected:
        # Fallback to standard claude folder
        detected.append(
            Account(
                name="primary",
                config_dir=str(home / ".claude"),
                priority=1,
                enabled=True,
            )
        )

    return detected


class ConfigManager:
    def __init__(self, config_path: Optional[Path] = None):
        self.config_dir = config_path.parent if config_path else DEFAULT_CONFIG_DIR
        self.config_file = config_path if config_path else CONFIG_FILE

    def ensure_config_dir(self):
        self.config_dir.mkdir(parents=True, exist_ok=True)

    def load_accounts(self) -> List[Account]:
        if not self.config_file.exists():
            accounts = get_default_accounts()
            self.save_accounts(accounts)
            return accounts

        try:
            with open(self.config_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            
            raw_accounts = data.get("accounts", [])
            accounts: List[Account] = []
            for item in raw_accounts:
                accounts.append(
                    Account(
                        name=item["name"],
                        config_dir=item["config_dir"],
                        priority=int(item.get("priority", 99)),
                        enabled=item.get("enabled", True),
                        email=item.get("email"),
                        org_name=item.get("org_name"),
                        subscription_type=item.get("subscription_type"),
                        rate_limited_until=item.get("rate_limited_until"),
                    )
                )
            # Sort by priority ascending (1 = highest priority)
            accounts.sort(key=lambda a: a.priority)
            return accounts
        except Exception:
            return get_default_accounts()

    def save_accounts(self, accounts: List[Account]):
        self.ensure_config_dir()
        # Sort before saving
        accounts.sort(key=lambda a: a.priority)
        data = {
            "version": "1.0",
            "accounts": [
                {
                    "name": a.name,
                    "config_dir": a.config_dir,
                    "priority": a.priority,
                    "enabled": a.enabled,
                    "email": a.email,
                    "org_name": a.org_name,
                    "subscription_type": a.subscription_type,
                    "rate_limited_until": a.rate_limited_until,
                }
                for a in accounts
            ],
            "settings": {
                "cooldown_minutes": 60,
                "auto_switch": True,
            }
        }
        with open(self.config_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

    def update_account_priority(self, account_name: str, new_priority: int) -> bool:
        accounts = self.load_accounts()
        target = next((a for a in accounts if a.name.lower() == account_name.lower()), None)
        if not target:
            return False

        other_accounts = [a for a in accounts if a.name.lower() != account_name.lower()]
        insert_idx = max(0, min(new_priority - 1, len(other_accounts)))
        other_accounts.insert(insert_idx, target)

        for idx, a in enumerate(other_accounts, start=1):
            a.priority = idx

        self.save_accounts(other_accounts)
        return True

    def reorder_priorities(self, account_names: List[str]) -> bool:
        accounts = self.load_accounts()
        acct_dict = {a.name.lower(): a for a in accounts}
        new_order: List[Account] = []

        for name in account_names:
            key = name.strip().lower()
            if key in acct_dict:
                new_order.append(acct_dict.pop(key))

        # Add any remaining accounts to the end
        new_order.extend(acct_dict.values())

        for idx, a in enumerate(new_order, start=1):
            a.priority = idx

        self.save_accounts(new_order)
        return True
