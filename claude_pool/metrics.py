import json
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Dict, Any, Optional
from claude_pool.models import Account, AccountStats, PoolStats, ModelUsage


def format_token_count(n: int) -> str:
    """Format large token counts into human readable strings like 116.5M, 450K."""
    if n >= 1_000_000_000:
        return f"{n / 1_000_000_000:.2f}B"
    if n >= 1_000_000:
        return f"{n / 1_000_000:.1f}M"
    if n >= 1_000:
        return f"{n / 1_000:.1f}K"
    return str(n)


class MetricsEngine:
    """
    Extracts and aggregates real-time token consumption directly from
    live project session transcripts (.jsonl) and stats-cache.json.
    """

    @classmethod
    def read_account_stats(cls, account: Account) -> AccountStats:
        config_path = account.resolved_path
        stats = AccountStats(account_name=account.name)

        # 1. Base lifetime metrics from stats-cache.json (if available)
        stats_file = config_path / "stats-cache.json"
        if stats_file.exists():
            try:
                with open(stats_file, "r", encoding="utf-8") as f:
                    raw = json.load(f)

                stats.total_sessions = raw.get("totalSessions", 0)
                stats.total_messages = raw.get("totalMessages", 0)

                raw_models = raw.get("modelUsage", {})
                for model_name, usage_dict in raw_models.items():
                    m_usage = ModelUsage(
                        input_tokens=usage_dict.get("inputTokens", 0),
                        output_tokens=usage_dict.get("outputTokens", 0),
                        cache_read_tokens=usage_dict.get("cacheReadInputTokens", 0),
                        cache_creation_tokens=usage_dict.get("cacheCreationInputTokens", 0),
                    )
                    stats.lifetime_models[model_name] = m_usage
                    stats.lifetime_total_input += m_usage.input_tokens
                    stats.lifetime_total_output += m_usage.output_tokens
                    stats.lifetime_total_cache += (
                        m_usage.cache_read_tokens + m_usage.cache_creation_tokens
                    )
                    stats.lifetime_total_tokens += m_usage.total_tokens
            except Exception:
                pass

        # 2. Real-time extraction from live project session .jsonl files for today
        proj_dir = config_path / "projects"
        if not proj_dir.exists():
            return stats

        today_utc = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        today_local = datetime.now().strftime("%Y-%m-%d")
        today_prefixes = (today_utc, today_local)

        cutoff_mtime = time.time() - (48 * 3600)
        session_count = 0

        for f in proj_dir.rglob("*.jsonl"):
            if "subagents" in str(f):
                continue

            try:
                stat_res = f.stat()
                session_count += 1
                if stat_res.st_mtime < cutoff_mtime:
                    continue

                with open(f, "r", encoding="utf-8", errors="ignore") as fp:
                    for line in fp:
                        if "input_tokens" not in line:
                            continue
                        data = json.loads(line)
                        ts = data.get("timestamp", "")
                        if not any(ts.startswith(prefix) for prefix in today_prefixes):
                            continue

                        msg = data.get("message", {})
                        usage = msg.get("usage", {})
                        model = msg.get("model", "unknown")

                        inp = usage.get("input_tokens", 0)
                        out = usage.get("output_tokens", 0)
                        c_read = usage.get("cache_read_input_tokens", 0)
                        c_create = usage.get("cache_creation_input_tokens", 0)
                        c_total = c_read + c_create
                        turn_tokens = inp + out + c_total

                        stats.today_input_tokens += inp
                        stats.today_output_tokens += out
                        stats.today_cache_read_tokens += c_read
                        stats.today_cache_creation_tokens += c_create
                        stats.today_total_tokens += turn_tokens

                        stats.today_tokens_by_model[model] = (
                            stats.today_tokens_by_model.get(model, 0) + turn_tokens
                        )

                        if model not in stats.today_models_detail:
                            stats.today_models_detail[model] = ModelUsage()
                        m_det = stats.today_models_detail[model]
                        m_det.input_tokens += inp
                        m_det.output_tokens += out
                        m_det.cache_read_tokens += c_read
                        m_det.cache_creation_tokens += c_create

            except Exception:
                continue

        if stats.total_sessions == 0:
            stats.total_sessions = session_count

        return stats

    @classmethod
    def get_pool_stats(cls, accounts: List[Account]) -> PoolStats:
        pool = PoolStats()
        for acct in accounts:
            acct_stats = cls.read_account_stats(acct)
            pool.accounts.append(acct_stats)
            pool.today_pool_tokens += acct_stats.today_total_tokens
            pool.today_pool_input += acct_stats.today_input_tokens
            pool.today_pool_output += acct_stats.today_output_tokens
            pool.today_pool_cache += (
                acct_stats.today_cache_read_tokens + acct_stats.today_cache_creation_tokens
            )

            pool.lifetime_pool_input += acct_stats.lifetime_total_input
            pool.lifetime_pool_output += acct_stats.lifetime_total_output
            pool.lifetime_pool_cache += acct_stats.lifetime_total_cache
            pool.lifetime_pool_tokens += acct_stats.lifetime_total_tokens
            pool.total_pool_sessions += acct_stats.total_sessions

        return pool
