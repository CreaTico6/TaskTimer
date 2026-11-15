"""Lightweight, rate-limited git auto-updater for TaskTimer."""

from __future__ import annotations

import shutil
import subprocess
import time
from pathlib import Path

from tasktimer.storage import get_data_dir

_CHECK_INTERVAL_SECONDS = 24 * 3600


def _repo_root() -> Path:
    return Path(__file__).resolve().parent.parent


def _last_check_file() -> Path:
    return get_data_dir() / ".last_update_check"


def should_check_now(check_file: Path | None = None, now: float | None = None) -> bool:
    """Return True if at least 24 hours have passed since the last update check."""
    marker = check_file or _last_check_file()
    if not marker.exists():
        return True
    try:
        last = float(marker.read_text(encoding="utf-8").strip())
        ref = time.time() if now is None else now
        return (ref - last) >= _CHECK_INTERVAL_SECONDS
    except (ValueError, OSError):
        return True


def _mark_checked(check_file: Path | None = None, now: float | None = None) -> None:
    marker = check_file or _last_check_file()
    marker.parent.mkdir(parents=True, exist_ok=True)
    marker.write_text(str(time.time() if now is None else now), encoding="utf-8")


def _run_git(repo: Path, args: list[str], timeout: int = 8) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", "-C", str(repo), *args],
        capture_output=True,
        text=True,
        timeout=timeout,
    )


def check_for_updates(force: bool = False) -> bool:
    """Check upstream for updates (at most once every 24h unless force=True).

    Returns True if an update was pulled.
    """
    repo = _repo_root()
    if not (repo / ".git").exists() or not shutil.which("git"):
        if force:
            print("Update check skipped (not a git checkout).")
        return False

    if not force and not should_check_now():
        return False

    _mark_checked()

    try:
        fetch = _run_git(repo, ["fetch", "--quiet"], timeout=6)
        if fetch.returncode != 0:
            if force:
                print("Could not reach remote repository.")
            return False

        behind = _run_git(repo, ["rev-list", "--count", "HEAD..@{u}"])
        if behind.returncode != 0 or int(behind.stdout.strip() or "0") == 0:
            if force:
                print("✔ TaskTimer is already up to date.")
            return False

        dirty = _run_git(repo, ["status", "--porcelain"])
        if dirty.stdout.strip():
            print("⚠ Updates available, but local changes exist; skipping auto-pull.")
            return False

        pull = _run_git(repo, ["pull", "--ff-only", "--quiet"], timeout=10)
        if pull.returncode == 0:
            print("🔄 TaskTimer updated to the latest version.")
            return True
        if force:
            print("⚠ Could not fast-forward automatically. Run 'git pull' manually.")
    except (subprocess.TimeoutExpired, ValueError, OSError):
        if force:
            print("Update check timed out.")
    return False
