import unittest
import tempfile
import shutil
from pathlib import Path
from claude_pool.models import Account, AccountStats, PoolStats, QuotaInfo
from claude_pool.config import ConfigManager
from claude_pool.session_sync import SessionSyncEngine, encode_project_name
from claude_pool.quota import QuotaEngine
from claude_pool.pool import AccountPoolManager
from claude_pool.detector import OutputDetector


class TestClaudePoolEndToEnd(unittest.TestCase):
    def setUp(self):
        self.tmp_dir = Path(tempfile.mkdtemp())
        self.cfg_file = self.tmp_dir / "config.json"
        self.mgr = ConfigManager(self.cfg_file)

        self.acct1_dir = self.tmp_dir / "acct1"
        self.acct2_dir = self.tmp_dir / "acct2"
        self.acct3_dir = self.tmp_dir / "acct3"
        self.acct1_dir.mkdir()
        self.acct2_dir.mkdir()
        self.acct3_dir.mkdir()

    def tearDown(self):
        shutil.rmtree(self.tmp_dir, ignore_errors=True)

    def test_priority_reordering(self):
        """Verify dynamic priority sorting and promotion/demotion."""
        accounts = [
            Account(name="primary", config_dir=str(self.acct1_dir), priority=1),
            Account(name="account4", config_dir=str(self.acct2_dir), priority=2),
            Account(name="account2", config_dir=str(self.acct3_dir), priority=3),
        ]
        self.mgr.save_accounts(accounts)

        # Promote account4 to Priority 1
        ok = self.mgr.update_account_priority("account4", 1)
        self.assertTrue(ok)
        reloaded = self.mgr.load_accounts()
        self.assertEqual(reloaded[0].name, "account4")
        self.assertEqual(reloaded[0].priority, 1)
        self.assertEqual(reloaded[1].name, "primary")
        self.assertEqual(reloaded[1].priority, 2)
        self.assertEqual(reloaded[2].name, "account2")
        self.assertEqual(reloaded[2].priority, 3)

    def test_session_sync_transfer(self):
        """Verify project path encoding and exact session JSONL file replication."""
        acct1 = Account(name="acct1", config_dir=str(self.acct1_dir), priority=1)
        acct2 = Account(name="acct2", config_dir=str(self.acct2_dir), priority=2)

        dummy_cwd = Path("E:/PP/accs")
        proj_name = encode_project_name(dummy_cwd)
        self.assertEqual(proj_name, "E--PP-accs")

        src_proj = self.acct1_dir / "projects" / proj_name
        src_proj.mkdir(parents=True)

        session_id = "test-session-uuid-1234"
        sample_data = '{"message": "Hello Claude", "timestamp": "2026-10-17T08:00:00Z"}'
        (src_proj / f"{session_id}.jsonl").write_text(sample_data, encoding="utf-8")

        # Perform cross-account transfer
        res = SessionSyncEngine.transfer_session(acct1, acct2, session_id=session_id, cwd_path=dummy_cwd)
        self.assertEqual(res, session_id)

        dst_proj = self.acct2_dir / "projects" / proj_name
        dst_file = dst_proj / f"{session_id}.jsonl"
        self.assertTrue(dst_file.exists())
        self.assertEqual(dst_file.read_text(encoding="utf-8"), sample_data)

    def test_failover_selection_logic(self):
        """Verify pool manager picks highest priority ready account and fails over upon exhaustion."""
        accounts = [
            Account(name="acct1", config_dir=str(self.acct1_dir), priority=1),
            Account(name="acct2", config_dir=str(self.acct2_dir), priority=2),
            Account(name="acct3", config_dir=str(self.acct3_dir), priority=3),
        ]
        self.mgr.save_accounts(accounts)
        pool = AccountPoolManager(self.mgr)

        # 1. Highest priority ready account is acct1
        active = pool.get_active_account()
        self.assertIsNotNone(active)
        self.assertEqual(active.name, "acct1")

        standby = pool.get_standby_accounts(current=active)
        self.assertEqual([a.name for a in standby], ["acct2", "acct3"])

        # 2. Simulate rate limit on acct1
        pool.mark_rate_limited(active, cooldown_seconds=3600)
        self.assertTrue(active.is_rate_limited)

        # 3. Next active must now seamlessly be acct2
        next_active = pool.get_active_account()
        self.assertIsNotNone(next_active)
        self.assertEqual(next_active.name, "acct2")

        # 4. Simulate rate limit on acct2
        pool.mark_rate_limited(next_active, cooldown_seconds=3600)
        third_active = pool.get_active_account()
        self.assertIsNotNone(third_active)
        self.assertEqual(third_active.name, "acct3")

    def test_detector_patterns(self):
        """Verify output detector correctly identifies rate limits and auth expirations."""
        is_event, ev_type = OutputDetector.check_line("Error: You've hit your usage limit, resets at 7:10pm")
        self.assertTrue(is_event)
        self.assertEqual(ev_type, "rate_limit")

        is_event, ev_type = OutputDetector.check_line("429 Too Many Requests: Rate limit exceeded")
        self.assertTrue(is_event)
        self.assertEqual(ev_type, "rate_limit")

        is_event, ev_type = OutputDetector.check_line("Failed to authenticate: OAuth session expired")
        self.assertTrue(is_event)
        self.assertEqual(ev_type, "auth_expired")

        is_event, ev_type = OutputDetector.check_line("Here is the Python code you requested...")
        self.assertFalse(is_event)
        self.assertIsNone(ev_type)


if __name__ == "__main__":
    unittest.main()
