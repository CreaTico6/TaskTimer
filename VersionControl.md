# Version Control — TaskTimer

**Author:** `creatico6@github.com`

> This file tracks all versions and changes made to **TaskTimer**. It must be updated whenever code or documentation changes.

## [0.3.0] — 2026-11-15

### Added / Changed
- `tasktimer/storage.py`: Added append-only permanent history log (`~/.local/share/tasktimer/history.jsonl`). Completed and removed tasks are archived to `history.jsonl` and cleared from `tasks.json`, automatically resetting `next_id` back to `1` whenever all tasks are completed or removed.
- `tasktimer/cli.py`: Added `tt history [-n LIMIT]` subcommand and `[8] History` option in the interactive menu.
- `tests/test_storage.py`, `README.md`, `CoderManual.md`: Updated tests and documentation for permanent history and automatic ID reset.

## [0.2.7] — 2026-11-15

### Changed
- `tasktimer/storage.py`: Reset `next_id` back to `1` whenever no tasks remain in `tasks.json`.
- `tests/test_storage.py`: Added `test_next_id_resets_when_all_tasks_removed`.

## [0.2.6] — 2026-11-15

### Changed
- `tasktimer/indicator.py`: `TaskTimerFloatingPill` now expands dynamically to display up to 3 active/open tasks (capping height at 3 tasks even when more exist) and shrinks back when tasks are completed or removed.

## [0.2.5] — 2026-11-15

### Changed
- `tasktimer/indicator.py`: Updated `TaskTimerFloatingPill` to a two-line layout showing `⏱ TiSoft TaskTimer` on the top line and the active task/timer (or `No active task`) on the second line.

## [0.2.4] — 2026-11-15

### Added
- `uninstall.sh`: interactive userspace uninstaller that stops the indicator, removes symlinks and the Fish hook, and optionally deletes saved task data and the repository directory.
- Updated `README.md`, `CoderManual.md`, and `VersionControl.md`.

## [0.2.3] — 2026-11-15

### Changed
- Relocated installation path from `~/Oficina/TaskTimer` to `~/Projects/TaskTimer` and updated `README.md` and `CoderManual.md` accordingly.

## [0.2.2] — 2026-11-15

### Added / Changed
- Added `LICENSE` (MIT License).
- Removed `plan.md` (superseded by `CoderManual.md`).
- Updated `README.md`, `CoderManual.md`, and `VersionControl.md` to reflect the current repository structure and remove dead links.

## [0.2.1] — 2026-11-15

### Changed
- Removed environment-specific institutional references from documentation (`README.md`, `plan.md`, `CoderManual.md`, `VersionControl.md`).

## [0.2.0] — 2026-11-15

### Added / Changed
- Added `CoderManual.md` with a TL;DR, full technical architecture, reproduction guide, and troubleshooting.
- Translated all documentation (`README.md`, `plan.md`, `VersionControl.md`, `CoderManual.md`), Fish prompt, and Python source files (CLI, indicator, storage, tests) to English, with author references (`creatico6@github.com`).

## [0.1.1] — 2026-11-15

### Fixed / Improved
- `tasktimer/indicator.py`: Detected that restricted GNOME sessions may not have `ubuntu-appindicators@ubuntu.com` installed/enabled in GNOME Shell. Added automatic fallback to an always-on-top, draggable GTK3 floating pill (`TaskTimerFloatingPill`) with overtime highlighting and dropdown menu, while preserving `AyatanaAppIndicator3` when the extension is enabled. Added `gi.require_version("Gdk", "3.0")` before importing `Gdk`.

## [0.1.0] — 2026-11-15

### Added
- Initial project structure in `/home/tnuno-mo/Oficina/TaskTimer`.
- `tasktimer/storage.py`: atomic JSON persistence in `~/.local/share/tasktimer/tasks.json`, duration parsing (`25m`, `1h30m`, `45s`), countdown and overtime calculation.
- `tasktimer/indicator.py`: GNOME top-bar indicator daemon with PID lock, dynamic menu, and `notify-send` alerts.
- `tasktimer/cli.py` and `bin/tasktimer`: interactive CLI and direct subcommands (`add`, `list`, `start`, `pause`, `done`, `addtime`, `rm`, `indicator`).
- `~/.config/fish/conf.d/tasktimer.fish`: once-per-login interactive prompt without modifying the `TiDefinitions` block in `~/.config/fish/config.fish`.
- `tests/test_storage.py`: unit test suite using stdlib `unittest`.
- `README.md`, `plan.md`, and `VersionControl.md`.
