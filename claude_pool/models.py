from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional
from pathlib import Path


@dataclass
class QuotaInfo:
    session_used_pct: Optional[int] = None
    session_remaining_pct: Optional[int] = None
    session_reset: Optional[str] = None
    week_used_pct: Optional[int] = None
    week_remaining_pct: Optional[int] = None
    week_reset: Optional[str] = None
    last_checked: Optional[float] = None

    @property
    def is_fresh(self) -> bool:
        """Cache is fresh for 5 minutes."""
        if not self.last_checked:
            return False
        return (datetime.now().timestamp() - self.last_checked) < 300


@dataclass
class Account:
    name: str
    config_dir: str
    priority: int
    enabled: bool = True
    email: Optional[str] = None
    org_name: Optional[str] = None
    subscription_type: Optional[str] = None
    auth_valid: Optional[bool] = None
    rate_limited_until: Optional[float] = None  # Epoch timestamp
    quota: Optional[QuotaInfo] = None

    @property
    def resolved_path(self) -> Path:
        return Path(self.config_dir).expanduser().resolve()

    @property
    def is_rate_limited(self) -> bool:
        if self.rate_limited_until is None:
            return False
        return datetime.now().timestamp() < self.rate_limited_until

    @property
    def is_ready(self) -> bool:
        return self.enabled and not self.is_rate_limited and (self.auth_valid is not False)


@dataclass
class ModelUsage:
    input_tokens: int = 0
    output_tokens: int = 0
    cache_read_tokens: int = 0
    cache_creation_tokens: int = 0

    @property
    def total_tokens(self) -> int:
        return (
            self.input_tokens
            + self.output_tokens
            + self.cache_read_tokens
            + self.cache_creation_tokens
        )


@dataclass
class AccountStats:
    account_name: str
    today_input_tokens: int = 0
    today_output_tokens: int = 0
    today_cache_read_tokens: int = 0
    today_cache_creation_tokens: int = 0
    today_total_tokens: int = 0
    today_tokens_by_model: Dict[str, int] = field(default_factory=dict)
    today_models_detail: Dict[str, ModelUsage] = field(default_factory=dict)

    lifetime_models: Dict[str, ModelUsage] = field(default_factory=dict)
    lifetime_total_input: int = 0
    lifetime_total_output: int = 0
    lifetime_total_cache: int = 0
    lifetime_total_tokens: int = 0

    total_sessions: int = 0
    total_messages: int = 0


@dataclass
class PoolStats:
    accounts: List[AccountStats] = field(default_factory=list)
    today_pool_tokens: int = 0
    today_pool_input: int = 0
    today_pool_output: int = 0
    today_pool_cache: int = 0

    lifetime_pool_input: int = 0
    lifetime_pool_output: int = 0
    lifetime_pool_cache: int = 0
    lifetime_pool_tokens: int = 0
    total_pool_sessions: int = 0
