# Version Control — TaskTimer

**Author:** `creatico6@github.com`

> This file tracks all versions and changes made to **TaskTimer**. It must be updated whenever code or documentation changes.

## [0.8.1] — 2026-11-15

### Added
- `Makefile`: Added `check-x11` target (runs before `install`) to warn and prompt `[y/N]` when `XDG_SESSION_TYPE` is not `x11`, while still allowing the user to proceed.
- Updated `tasktimer/__init__.py`, `README.md`, and `VersionControl.md`.

## [0.8.0] — 2026-11-15

### Added
- `tasktimer/updater.py`: Added rate-limited auto-update check (at most once every 24h via `~/.local/share/tasktimer/.last_update_check`), using `git fetch` + `git pull --ff-only` when the working tree is clean.
- `tasktimer/cli.py`: Runs the 24h update check on `tt --startup` and adds `tt update` for manual update checks.
- `tests/test_storage.py`: Added `UpdaterCooldownTests` covering the 24-hour cooldown.
- Updated `tasktimer/__init__.py`, `README.md`, `CoderManual.md`, and `VersionControl.md`.

## [0.7.2] — 2026-11-15

### Changed
- `tasktimer/__init__.py`: Synchronized `__version__` to `"0.7.2"`.
- `CoderManual.md`: Updated TL;DR, project layout, and runtime files to reflect `Makefile`, `TaskTimerCardPopup`, `history.jsonl`, `indicator.log`, and `gnome-extension/tasktimer@creatico6`.
- `Oficina/randomstuff/TiDefinitions.sh`: Simplified TaskTimer installation to invoke `make -C "$TT_DIR" install`.

## [0.7.1] — 2026-11-15

### Changed
- `Makefile`: Made the post-install `Alt+F2 -> r -> Enter` (or re-login) GNOME Shell reload instruction explicit and prominent in `gnome-ext` / `make install`.

## [0.7.0] — 2026-11-15

### Added
- `tasktimer/indicator.py`: Added a `"✕"` close button to the always-on-top `TaskTimerFloatingPill` header bar.
- `tasktimer/cli.py`: Added `tt indicator toggle` action.
- `gnome-extension/tasktimer@creatico6/`: Added a userspace GNOME Shell extension (GNOME 42–44) placing a permanent `⏱` button in the GNOME top bar to toggle the floating TaskTimer widget.
- `Makefile`, `uninstall.sh`, `README.md`: Integrated `make gnome-ext` installation and uninstallation.

## [0.6.2] — 2026-11-15

### Added
- `tasktimer/indicator.py`: Added a top header bar with `"⏱ TiSoft TaskTimer"` and a `"✕"` close button to `TaskTimerCardPopup` to dismiss the popup card.

## [0.6.1] — 2026-11-15

### Fixed
- `tasktimer/indicator.py`: Removed `set_app_paintable(True)` in `_enable_rgba()` and set `rgba(30, 34, 42, 0.95)` background on `window.tasktimer-card` and `rgba(30, 34, 42, 0.94)` on `window.tasktimer-pill` so the windows render solid/high-opacity with transparent rounded corners.

## [0.6.0] — 2026-11-15

### Added / Changed
- `tasktimer/indicator.py`: Brought full feature parity with the terminal CLI to `TaskTimerCardPopup`:
  - Inline **New Task** creation form (`➕ New` with title, description, duration, and immediate start toggle).
  - Both **`-5m` and `+5m`** time adjustment buttons with inline validation.
  - Task **removal** (`🗑`) on both active and queued tasks.
  - Inline **Permanent History** view (`📜 History`, last 10 entries).
  - Enabled RGBA visuals (`_enable_rgba`) on both the floating pill and card popup so CSS `border-radius: 12px` renders smooth, transparent rounded corners on X11.

## [0.5.2] — 2026-11-15

### Fixed / Improved
- `tasktimer/indicator.py`: Added `_find_gtk_python()` to fall back to `/usr/bin/python3` when the active `PATH` Python lacks `PyGObject`, logged background stderr to `~/.local/share/tasktimer/indicator.log`, guarded `monitor is None` in `_position_near()`, and ignored spurious `focus-out-event` within 150ms of opening `TaskTimerCardPopup`.
- `Makefile`: Added `deps` target (runs during `make install`) that checks for `Gtk 3.0`/`Gdk 3.0` bindings and installs `PyGObject` in userspace only if missing.

## [0.5.1] — 2026-11-15

### Added
- `Makefile`: Added `help` target (`make help`) and documented it in `README.md`.

## [0.5.0] — 2026-11-15

### Added / Changed
- `Makefile`: Added `install` (default), `fish`, `test`, and `uninstall` targets so `git clone ... && cd TaskTimer && make` installs everything in one step.
- `README.md`, `CoderManual.md`, `VersionControl.md`: Updated installation instructions to use `make`.

## [0.4.3] — 2026-11-15

### Changed
- `README.md`: Added explicit step-by-step installation instructions (requirements, `git clone`, `chmod +x`, `~/.local/bin` symlinks, `PATH`, and optional Fish startup hook).

## [0.4.2] — 2026-11-15

### Added / Changed
- `README.md`: Embedded preview image `TaskTimer.jpg`.
- `CoderManual.md`, `VersionControl.md`: Documented `TaskTimer.jpg` in the project layout.

## [0.4.1] — 2026-11-15

### Changed
- `tasktimer/indicator.py`: Removed the `"✕ Close"` button from the `TaskTimerCardPopup` footer, keeping `"🖥 Terminal"`.

## [0.4.0] — 2026-11-15

### Added / Changed
- `tasktimer/indicator.py`: Replaced the plain `Gtk.Menu` on the floating pill with `TaskTimerCardPopup`, a dark rounded GTK3 card featuring the active task title/description, live countdown, `Gtk.ProgressBar`, horizontal action buttons (`Pause/Resume`, `Done`, `+5m`), clickable task-switcher buttons, and `Terminal` / `Close` footer buttons.

## [0.3.5] — 2026-11-15

### Changed
- `tasktimer/indicator.py`: Grouped all 4 active-task menu rows (header, Pause/Resume, Complete, Add +5 min) under `tasktimer-menu-section` (blue tint + left accent + hover highlight) and removed the blue background from `"Switch / Start task:"`.

## [0.3.4] — 2026-11-15

### Changed
- `tasktimer/indicator.py`: Removed the blue left accent border from the `"Switch / Start task:"` menu subheader (`tasktimer-menu-subheader`) while keeping it on the active task header (`tasktimer-menu-section`).

## [0.3.3] — 2026-11-15

### Changed
- `tasktimer/indicator.py`: Added a subtle tinted background and left accent border (`menuitem.tasktimer-menu-section`) to non-clickable menu headers so they are visually distinct from clickable actions.

## [0.3.2] — 2026-11-15

### Changed
- `tasktimer/indicator.py`: Styled the active task header and `"Switch / Start task:"` menu headers in bold with full contrast (no longer dimmed by GTK's disabled menu item styling).

## [0.3.1] — 2026-11-15

### Changed
- `tasktimer/storage.py`: Added `parse_signed_duration()` and updated `TaskStore.add_time()` to support both positive and negative adjustments while ensuring `allocated_seconds` stays above zero.
- `tasktimer/cli.py`: Updated interactive option `[5] +/-Time` and `tt addtime` to accept both adding (`+5m`, `5m`) and subtracting (`-5m`, `-30s`) time.
- `tests/test_storage.py`: Added unit tests for signed durations and negative time adjustments.

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
