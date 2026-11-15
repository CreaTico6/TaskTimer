"""Persistence layer and timer logic for TaskTimer."""

from __future__ import annotations

import json
import os
import re
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

_DURATION_PART_RE = re.compile(r"(\d+)\s*([hms])?", re.IGNORECASE)


def get_data_dir() -> Path:
    """Return the user data directory (XDG_DATA_HOME/tasktimer)."""
    base = os.environ.get("XDG_DATA_HOME")
    root = Path(base) if base else Path.home() / ".local" / "share"
    return root / "tasktimer"


def get_runtime_dir() -> Path:
    """Return the session runtime directory (XDG_RUNTIME_DIR or /tmp)."""
    runtime = os.environ.get("XDG_RUNTIME_DIR")
    if runtime:
        return Path(runtime)
    return Path(tempfile.gettempdir())


def parse_duration(spec: str) -> int:
    """Parse a duration string (e.g. '25m', '1h30m', '45', '90s') into seconds.

    A bare integer without a unit is interpreted as minutes.
    """
    text = spec.strip().lower()
    if not text:
        raise ValueError("Duration cannot be empty.")

    if text.isdigit():
        seconds = int(text) * 60
        if seconds <= 0:
            raise ValueError("Duration must be greater than zero.")
        return seconds

    matches = list(_DURATION_PART_RE.finditer(text))
    if not matches or "".join(m.group(0) for m in matches).replace(" ", "") != text.replace(" ", ""):
        raise ValueError(f"Invalid duration format: '{spec}'. Use e.g. 25m, 1h30m, 45s, or 25.")

    total = 0
    for match in matches:
        value = int(match.group(1))
        unit = (match.group(2) or "m").lower()
        multiplier = {"h": 3600, "m": 60, "s": 1}[unit]
        total += value * multiplier

    if total <= 0:
        raise ValueError("Duration must be greater than zero.")
    return total


def format_duration(seconds: int, show_sign: bool = False) -> str:
    """Format seconds as HH:MM:SS or MM:SS (with optional '+' prefix for overtime)."""
    sign = ""
    if seconds < 0:
        sign = "+" if show_sign else "-"
        seconds = abs(seconds)
    hours, rem = divmod(int(seconds), 3600)
    minutes, secs = divmod(rem, 60)
    if hours > 0:
        return f"{sign}{hours:02d}:{minutes:02d}:{secs:02d}"
    return f"{sign}{minutes:02d}:{secs:02d}"


def current_elapsed(task: dict[str, Any], now: float | None = None) -> int:
    """Compute total elapsed seconds for a task."""
    elapsed = int(task.get("elapsed_seconds", 0))
    if task.get("status") == "running" and task.get("started_at") is not None:
        ref = time.time() if now is None else now
        elapsed += max(0, int(ref - float(task["started_at"])))
    return elapsed


def remaining_seconds(task: dict[str, Any], now: float | None = None) -> int:
    """Compute remaining seconds (negative when in overtime)."""
    return int(task.get("allocated_seconds", 0)) - current_elapsed(task, now=now)


class TaskStore:
    """Manage active tasks with atomic JSON writes and an append-only history log."""

    def __init__(self, path: Path | None = None) -> None:
        self.path = path or (get_data_dir() / "tasks.json")
        self.history_path = self.path.parent / "history.jsonl"

    def _append_history(self, task: dict[str, Any], event: str) -> None:
        self.history_path.parent.mkdir(parents=True, exist_ok=True)
        entry = {
            "event": event,
            "recorded_at": datetime.now(timezone.utc).isoformat(),
            "id": task["id"],
            "title": task["title"],
            "description": task.get("description", ""),
            "allocated_seconds": task["allocated_seconds"],
            "elapsed_seconds": task["elapsed_seconds"],
            "created_at": task.get("created_at"),
            "completed_at": task.get("completed_at"),
        }
        with self.history_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(entry, ensure_ascii=False) + "\n")

    def list_history(self, limit: int | None = 20) -> list[dict[str, Any]]:
        """Return permanent history entries, most recent first."""
        if not self.history_path.exists():
            return []
        entries: list[dict[str, Any]] = []
        with self.history_path.open("r", encoding="utf-8") as handle:
            for line in handle:
                line = line.strip()
                if line:
                    entries.append(json.loads(line))
        entries.reverse()
        return entries[:limit] if limit is not None else entries

    def _load_raw(self) -> dict[str, Any]:
        if not self.path.exists():
            return {"next_id": 1, "tasks": []}
        with self.path.open("r", encoding="utf-8") as handle:
            data = json.load(handle)
        data.setdefault("next_id", 1)
        data.setdefault("tasks", [])
        return data

    def _save_raw(self, data: dict[str, Any]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        fd, tmp_name = tempfile.mkstemp(prefix=".tasks_", suffix=".tmp", dir=str(self.path.parent))
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                json.dump(data, handle, ensure_ascii=False, indent=2)
            os.replace(tmp_name, self.path)
        except Exception:
            if os.path.exists(tmp_name):
                os.unlink(tmp_name)
            raise

    @staticmethod
    def _find_task(data: dict[str, Any], task_id: int) -> dict[str, Any]:
        for task in data["tasks"]:
            if int(task["id"]) == int(task_id):
                return task
        raise KeyError(f"Task #{task_id} not found.")

    @staticmethod
    def _pause_running(data: dict[str, Any], now: float) -> dict[str, Any] | None:
        for task in data["tasks"]:
            if task["status"] == "running":
                task["elapsed_seconds"] = current_elapsed(task, now=now)
                task["started_at"] = None
                task["status"] = "paused"
                return task
        return None

    def list_tasks(self, include_done: bool = True) -> list[dict[str, Any]]:
        """Return tasks ordered by status (active first) and ID."""
        data = self._load_raw()
        tasks = data["tasks"]
        if not include_done:
            tasks = [t for t in tasks if t["status"] != "done"]
        order = {"running": 0, "paused": 1, "pending": 2, "done": 3}
        return sorted(tasks, key=lambda t: (order.get(t["status"], 9), int(t["id"])))

    def get_active_task(self) -> dict[str, Any] | None:
        """Return the currently running task, or the first paused task if any."""
        tasks = self._load_raw()["tasks"]
        for status in ("running", "paused"):
            for task in tasks:
                if task["status"] == status:
                    return task
        return None

    def add_task(self, title: str, allocated_seconds: int, description: str = "") -> dict[str, Any]:
        """Create and persist a new task."""
        clean_title = title.strip()
        if not clean_title:
            raise ValueError("Task title cannot be empty.")
        if allocated_seconds <= 0:
            raise ValueError("Allocated time must be greater than zero.")

        data = self._load_raw()
        if not data["tasks"]:
            data["next_id"] = 1
        task_id = int(data["next_id"])
        data["next_id"] = task_id + 1
        task = {
            "id": task_id,
            "title": clean_title,
            "description": description.strip(),
            "allocated_seconds": int(allocated_seconds),
            "elapsed_seconds": 0,
            "status": "pending",
            "started_at": None,
            "notified_overtime": False,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "completed_at": None,
        }
        data["tasks"].append(task)
        self._save_raw(data)
        return task

    def start_task(self, task_id: int) -> dict[str, Any]:
        """Start or resume a task, automatically pausing any other running task."""
        now = time.time()
        data = self._load_raw()
        target = self._find_task(data, task_id)
        if target["status"] == "done":
            raise ValueError(f"Task #{task_id} is already completed.")
        if target["status"] == "running":
            return target
        self._pause_running(data, now)
        target["status"] = "running"
        target["started_at"] = now
        self._save_raw(data)
        return target

    def pause_active(self) -> dict[str, Any] | None:
        """Pause the currently running task, if any."""
        now = time.time()
        data = self._load_raw()
        paused = self._pause_running(data, now)
        if paused is not None:
            self._save_raw(data)
        return paused

    def toggle_active(self) -> dict[str, Any] | None:
        """Toggle between pausing the running task or resuming a paused task."""
        now = time.time()
        data = self._load_raw()
        paused = self._pause_running(data, now)
        if paused is not None:
            self._save_raw(data)
            return paused
        for task in data["tasks"]:
            if task["status"] == "paused":
                task["status"] = "running"
                task["started_at"] = now
                self._save_raw(data)
                return task
        return None

    def complete_task(self, task_id: int | None = None) -> dict[str, Any]:
        """Archive a task (or current active task) to permanent history and reset IDs if empty."""
        now = time.time()
        data = self._load_raw()
        if task_id is None:
            active = next((t for t in data["tasks"] if t["status"] in ("running", "paused")), None)
            if active is None:
                raise KeyError("No active task to complete.")
            target = active
        else:
            target = self._find_task(data, task_id)

        target["elapsed_seconds"] = current_elapsed(target, now=now)
        target["started_at"] = None
        target["status"] = "done"
        target["completed_at"] = datetime.now(timezone.utc).isoformat()
        self._append_history(target, "completed")
        data["tasks"] = [t for t in data["tasks"] if int(t["id"]) != int(target["id"])]
        if not data["tasks"]:
            data["next_id"] = 1
        self._save_raw(data)
        return target

    def add_time(self, task_id: int, extra_seconds: int) -> dict[str, Any]:
        """Add allocated time to a task and reset overtime alert if remaining > 0."""
        if extra_seconds <= 0:
            raise ValueError("Additional time must be greater than zero.")
        data = self._load_raw()
        target = self._find_task(data, task_id)
        target["allocated_seconds"] = int(target["allocated_seconds"]) + int(extra_seconds)
        if remaining_seconds(target) > 0:
            target["notified_overtime"] = False
        self._save_raw(data)
        return target

    def mark_notified_overtime(self, task_id: int) -> None:
        """Record that the overtime notification has been sent."""
        data = self._load_raw()
        target = self._find_task(data, task_id)
        if not target.get("notified_overtime"):
            target["notified_overtime"] = True
            self._save_raw(data)

    def remove_task(self, task_id: int) -> dict[str, Any]:
        """Archive a removed task to permanent history and reset next_id if no tasks remain."""
        now = time.time()
        data = self._load_raw()
        target = self._find_task(data, task_id)
        target["elapsed_seconds"] = current_elapsed(target, now=now)
        target["started_at"] = None
        self._append_history(target, "removed")
        data["tasks"] = [t for t in data["tasks"] if int(t["id"]) != int(task_id)]
        if not data["tasks"]:
            data["next_id"] = 1
        self._save_raw(data)
        return target
