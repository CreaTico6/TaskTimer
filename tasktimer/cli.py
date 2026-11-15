"""Interactive CLI and direct subcommands for TaskTimer."""

from __future__ import annotations

import argparse
import sys
from typing import Any

from tasktimer.indicator import (
    is_indicator_running,
    read_indicator_pid,
    start_indicator_background,
    stop_indicator,
)
from tasktimer.storage import (
    TaskStore,
    format_duration,
    parse_duration,
    parse_signed_duration,
    remaining_seconds,
)

_STATUS_BADGE = {
    "running": "▶ RUNNING ",
    "paused": "⏸ PAUSED  ",
    "pending": "• PENDING ",
    "done": "✔ DONE    ",
}


def _print_tasks(tasks: list[dict[str, Any]]) -> None:
    ind_state = "ACTIVE" if is_indicator_running() else "INACTIVE"
    print(f"\n=== TaskTimer | Top-bar indicator: {ind_state} ===")
    if not tasks:
        print("  (No tasks recorded.)\n")
        return

    print(f"  {'ID':<4} {'Status':<11} {'Remaining':<10} {'Allocated':<9} {'Title / Description'}")
    print("  " + "-" * 72)
    for task in tasks:
        badge = _STATUS_BADGE.get(task["status"], task["status"])
        rem = format_duration(remaining_seconds(task), show_sign=True)
        alloc = format_duration(int(task["allocated_seconds"]))
        desc = f" — {task['description']}" if task.get("description") else ""
        print(f"  {task['id']:<4} {badge:<11} {rem:<10} {alloc:<9} {task['title']}{desc}")
    print()


def _print_history(entries: list[dict[str, Any]]) -> None:
    print("\n=== TaskTimer | Permanent History ===")
    if not entries:
        print("  (No history recorded yet.)\n")
        return
    print(f"  {'Date':<17} {'Event':<10} {'Elapsed':<9} {'Allocated':<9} {'Title / Description'}")
    print("  " + "-" * 74)
    for item in entries:
        date_str = str(item.get("recorded_at", ""))[:16].replace("T", " ")
        elapsed = format_duration(int(item.get("elapsed_seconds", 0)))
        alloc = format_duration(int(item.get("allocated_seconds", 0)))
        desc = f" — {item['description']}" if item.get("description") else ""
        print(f"  {date_str:<17} {item['event']:<10} {elapsed:<9} {alloc:<9} {item['title']}{desc}")
    print()


def _prompt_int(label: str) -> int | None:
    raw = input(label).strip()
    if not raw:
        return None
    return int(raw)


def _interactive_new_task(store: TaskStore) -> None:
    title = input("Task title: ").strip()
    if not title:
        print("Cancelled.")
        return
    description = input("Description (optional): ").strip()
    dur_raw = input("Allocated time (e.g. 25m, 1h30m, 45s) [25m]: ").strip() or "25m"
    seconds = parse_duration(dur_raw)
    task = store.add_task(title, seconds, description)
    print(f"✔ Task #{task['id']} created ({format_duration(seconds)}).")
    start_now = input("Start this task now? [Y/n]: ").strip().lower()
    if start_now in ("", "y", "yes", "s", "sim"):
        store.start_task(int(task["id"]))
        started, _ = start_indicator_background()
        msg = " and top-bar indicator started." if started else "."
        print(f"▶ Task #{task['id']} started{msg}")


def _interactive_loop(store: TaskStore, startup: bool = False) -> int:
    if startup:
        started, _ = start_indicator_background()
        if started:
            print("⏱  Top-bar indicator started.")

    while True:
        _print_tasks(store.list_tasks(include_done=True))
        print(
            "[1] New task      [2] Start/Switch     [3] Pause/Resume     [4] Complete\n"
            "[5] +/-Time       [6] Remove           [7] Indicator (on/off) [8] History   [0] Exit"
        )
        try:
            choice = input("\nOption: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nGoodbye!")
            return 0

        try:
            if choice == "0" or choice.lower() in ("q", "quit", "exit"):
                return 0
            if choice == "1":
                _interactive_new_task(store)
            elif choice == "2":
                tid = _prompt_int("Task ID to start: ")
                if tid is not None:
                    task = store.start_task(tid)
                    start_indicator_background()
                    print(f"▶ Running: #{task['id']} {task['title']}")
            elif choice == "3":
                toggled = store.toggle_active()
                if toggled is None:
                    print("No running or paused task.")
                else:
                    state = "running" if toggled["status"] == "running" else "paused"
                    print(f"Task #{toggled['id']} is now {state}.")
            elif choice == "4":
                raw = input("Task ID to complete (Enter = current active): ").strip()
                tid = int(raw) if raw else None
                done = store.complete_task(tid)
                print(f"✔ Task #{done['id']} '{done['title']}' completed!")
            elif choice == "5":
                tid = _prompt_int("Task ID: ")
                if tid is not None:
                    delta_raw = input("Time adjustment (e.g. +5m, -5m, 10m) [+5m]: ").strip() or "+5m"
                    updated = store.add_time(tid, parse_signed_duration(delta_raw))
                    print(f"⏱ Task #{updated['id']} allocated time: {format_duration(updated['allocated_seconds'])}.")
            elif choice == "6":
                tid = _prompt_int("Task ID to remove: ")
                if tid is not None:
                    removed = store.remove_task(tid)
                    print(f"🗑 Task #{removed['id']} '{removed['title']}' removed.")
            elif choice == "7":
                if is_indicator_running():
                    stop_indicator()
                    print("Indicator stopped.")
                else:
                    started, pid = start_indicator_background()
                    if started or pid:
                        print(f"Indicator active (PID {pid}).")
                    else:
                        print("Could not start indicator (no DISPLAY/WAYLAND_DISPLAY).")
            elif choice == "8":
                _print_history(store.list_history(limit=20))
            else:
                print("Invalid option.")
        except (ValueError, KeyError) as exc:
            print(f"Error: {exc}")
        except (EOFError, KeyboardInterrupt):
            print("\nCancelled.")


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="tasktimer", description="Terminal task manager with top-bar indicator.")
    parser.add_argument("--startup", action="store_true", help="Ensure the indicator is running and open interactive mode.")
    sub = parser.add_subparsers(dest="command")

    p_add = sub.add_parser("add", help="Create a new task.")
    p_add.add_argument("title", help="Task title.")
    p_add.add_argument("duration", nargs="?", default="25m", help="Allocated time (e.g. 25m, 1h30m, 45s).")
    p_add.add_argument("-d", "--description", default="", help="Optional description.")
    p_add.add_argument("--start", action="store_true", help="Start immediately after creation.")

    p_list = sub.add_parser("list", help="List tasks.")
    p_list.add_argument("--active-only", action="store_true", help="Hide completed tasks.")

    p_start = sub.add_parser("start", help="Start or resume a task by ID.")
    p_start.add_argument("id", type=int, help="Task ID.")

    sub.add_parser("pause", help="Pause the currently running task.")

    p_done = sub.add_parser("done", help="Complete a task (or the current active task).")
    p_done.add_argument("id", type=int, nargs="?", help="Optional task ID.")

    p_addtime = sub.add_parser("addtime", help="Add or subtract allocated time (e.g. 5m or -- -5m).")
    p_addtime.add_argument("id", type=int, help="Task ID.")
    p_addtime.add_argument("duration", nargs="?", default="5m", help="Time adjustment (e.g. +5m, -5m).")

    p_rm = sub.add_parser("rm", help="Remove a task by ID.")
    p_rm.add_argument("id", type=int, help="Task ID.")

    p_ind = sub.add_parser("indicator", help="Manage the top-bar indicator.")
    p_ind.add_argument("action", choices=["start", "stop", "status", "toggle"], help="Indicator action.")

    p_hist = sub.add_parser("history", help="Show permanent task history.")
    p_hist.add_argument("-n", "--limit", type=int, default=20, help="Maximum entries to show.")

    return parser


def main(argv: list[str] | None = None) -> int:
    """CLI entry point."""
    parser = _build_parser()
    args = parser.parse_args(argv)
    store = TaskStore()

    if args.command is None:
        return _interactive_loop(store, startup=args.startup)

    try:
        if args.command == "add":
            task = store.add_task(args.title, parse_duration(args.duration), args.description)
            print(f"✔ Task #{task['id']} created: {task['title']} ({format_duration(task['allocated_seconds'])})")
            if args.start:
                store.start_task(int(task["id"]))
                start_indicator_background()
                print(f"▶ Task #{task['id']} started.")
        elif args.command == "list":
            _print_tasks(store.list_tasks(include_done=not args.active_only))
        elif args.command == "start":
            task = store.start_task(args.id)
            start_indicator_background()
            print(f"▶ Task #{task['id']} started: {task['title']}")
        elif args.command == "pause":
            paused = store.pause_active()
            if paused is None:
                print("No running task.")
            else:
                print(f"⏸ Task #{paused['id']} paused.")
        elif args.command == "done":
            done = store.complete_task(args.id)
            print(f"✔ Task #{done['id']} '{done['title']}' completed.")
        elif args.command == "addtime":
            updated = store.add_time(args.id, parse_signed_duration(args.duration))
            print(f"⏱ Task #{updated['id']} now has {format_duration(updated['allocated_seconds'])} allocated.")
        elif args.command == "rm":
            removed = store.remove_task(args.id)
            print(f"🗑 Task #{removed['id']} '{removed['title']}' removed.")
        elif args.command == "indicator":
            if args.action == "start":
                started, pid = start_indicator_background()
                if started:
                    print(f"Indicator started (PID {pid}).")
                elif pid:
                    print(f"Indicator is already active (PID {pid}).")
                else:
                    print("No graphical session (DISPLAY/WAYLAND_DISPLAY).")
                    return 1
            elif args.action == "stop":
                print("Indicator stopped." if stop_indicator() else "Indicator was not running.")
            elif args.action == "toggle":
                if is_indicator_running():
                    stop_indicator()
                    print("Indicator stopped.")
                else:
                    started, pid = start_indicator_background()
                    if started or pid:
                        print(f"Indicator started (PID {pid}).")
                    else:
                        print("No graphical session (DISPLAY/WAYLAND_DISPLAY).")
                        return 1
            elif args.action == "status":
                pid = read_indicator_pid()
                print(f"Indicator ACTIVE (PID {pid})." if pid else "Indicator INACTIVE.")
        elif args.command == "history":
            _print_history(store.list_history(limit=args.limit))
    except (ValueError, KeyError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
