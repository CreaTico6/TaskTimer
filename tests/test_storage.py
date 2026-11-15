"""Unit tests for the TaskTimer persistence and timing layer."""

import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tasktimer.storage import (
    TaskStore,
    current_elapsed,
    format_duration,
    parse_duration,
    remaining_seconds,
)


class DurationParsingTests(unittest.TestCase):
    def test_parse_units(self) -> None:
        self.assertEqual(parse_duration("25m"), 1500)
        self.assertEqual(parse_duration("1h30m"), 5400)
        self.assertEqual(parse_duration("45s"), 45)
        self.assertEqual(parse_duration("15"), 900)

    def test_parse_invalid(self) -> None:
        for bad in ("", "0m", "-5m", "abc"):
            with self.assertRaises(ValueError):
                parse_duration(bad)

    def test_format_duration(self) -> None:
        self.assertEqual(format_duration(90), "01:30")
        self.assertEqual(format_duration(3661), "01:01:01")
        self.assertEqual(format_duration(-12, show_sign=True), "+00:12")


class TaskStoreTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.store = TaskStore(Path(self._tmp.name) / "tasks.json")

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def test_add_start_switch_and_complete(self) -> None:
        t1 = self.store.add_task("Study C", 1500, "Pointers")
        t2 = self.store.add_task("Review PR", 600)

        self.store.start_task(t1["id"])
        active = self.store.get_active_task()
        self.assertIsNotNone(active)
        self.assertEqual(active["id"], t1["id"])
        self.assertEqual(active["status"], "running")

        # Starting t2 must automatically pause t1
        self.store.start_task(t2["id"])
        tasks = {t["id"]: t for t in self.store.list_tasks()}
        self.assertEqual(tasks[t1["id"]]["status"], "paused")
        self.assertEqual(tasks[t2["id"]]["status"], "running")

        done = self.store.complete_task(t2["id"])
        self.assertEqual(done["status"], "done")
        self.assertIsNotNone(done["completed_at"])

    def test_add_time_resets_overtime_flag(self) -> None:
        t = self.store.add_task("Sprint", 10)
        self.store.mark_notified_overtime(t["id"])
        updated = self.store.add_time(t["id"], 300)
        self.assertEqual(updated["allocated_seconds"], 310)
        self.assertFalse(updated["notified_overtime"])

    def test_remaining_and_overtime_calculation(self) -> None:
        task = {
            "allocated_seconds": 60,
            "elapsed_seconds": 50,
            "status": "running",
            "started_at": 1000.0,
        }
        self.assertEqual(current_elapsed(task, now=1005.0), 55)
        self.assertEqual(remaining_seconds(task, now=1005.0), 5)
        self.assertEqual(remaining_seconds(task, now=1020.0), -10)

    def test_next_id_resets_when_all_tasks_removed(self) -> None:
        t1 = self.store.add_task("First", 60)
        t2 = self.store.add_task("Second", 60)
        self.assertEqual((t1["id"], t2["id"]), (1, 2))
        self.store.remove_task(1)
        self.store.remove_task(2)
        t3 = self.store.add_task("Fresh", 60)
        self.assertEqual(t3["id"], 1)


if __name__ == "__main__":
    unittest.main()
