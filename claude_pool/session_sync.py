import os
import shutil
from pathlib import Path
from typing import Optional, Tuple
from claude_pool.models import Account


def encode_project_name(cwd_path: Optional[Path] = None) -> str:
    """Encode working directory into Claude project folder name (cross-platform)."""
    p = (cwd_path or Path.cwd()).resolve()
    if p.drive:
        # Windows: E:\PP\accs -> E--PP-accs
        drive = p.drive.replace(":", "")
        parts = p.parts[1:]
        if not parts:
            return f"{drive}--"
        return f"{drive}--" + "-".join(parts)
    else:
        # macOS / Linux: /home/user/app -> -home-user-app
        parts = [part for part in p.parts if part and part != "/"]
        return "-" + "-".join(parts)


class SessionSyncEngine:
    """Finds active/recent session and replicates it to target account directory."""

    @staticmethod
    def get_latest_session_id(account: Account, cwd_path: Optional[Path] = None) -> Optional[str]:
        p = (cwd_path or Path.cwd()).resolve()
        proj_name = encode_project_name(p)
        proj_dir = account.resolved_path / "projects" / proj_name

        if not proj_dir.exists():
            return None

        # Find newest .jsonl in this project dir
        jsonl_files = [f for f in proj_dir.glob("*.jsonl") if f.is_file()]
        if not jsonl_files:
            return None

        jsonl_files.sort(key=lambda f: f.stat().st_mtime, reverse=True)
        return jsonl_files[0].stem

    @classmethod
    def transfer_session(
        cls,
        source_account: Account,
        target_account: Account,
        session_id: Optional[str] = None,
        cwd_path: Optional[Path] = None,
    ) -> Optional[str]:
        """
        Transfers session jsonl and associated tool-results/subagents
        from source_account to target_account.
        Returns the transferred session_id, or None if no session found.
        """
        cwd = (cwd_path or Path.cwd()).resolve()
        proj_name = encode_project_name(cwd)

        src_proj_dir = source_account.resolved_path / "projects" / proj_name
        dst_proj_dir = target_account.resolved_path / "projects" / proj_name

        if not src_proj_dir.exists():
            return None

        if not session_id:
            session_id = cls.get_latest_session_id(source_account, cwd)
            if not session_id:
                return None

        src_session_file = src_proj_dir / f"{session_id}.jsonl"
        if not src_session_file.exists():
            return None

        # Ensure destination directory exists
        dst_proj_dir.mkdir(parents=True, exist_ok=True)
        dst_session_file = dst_proj_dir / f"{session_id}.jsonl"

        # Copy session transcript
        shutil.copy2(src_session_file, dst_session_file)

        # Copy any sidecar directory (tool-results, subagents, custom-title.json)
        src_sidecar_dir = src_proj_dir / session_id
        if src_sidecar_dir.exists() and src_sidecar_dir.is_dir():
            dst_sidecar_dir = dst_proj_dir / session_id
            if dst_sidecar_dir.exists():
                shutil.rmtree(dst_sidecar_dir)
            shutil.copytree(src_sidecar_dir, dst_sidecar_dir)

        # Copy custom-title.json if it exists inside sidecar or folder
        title_file = src_proj_dir / "custom-title.json"
        if title_file.exists():
            shutil.copy2(title_file, dst_proj_dir / "custom-title.json")

        return session_id
