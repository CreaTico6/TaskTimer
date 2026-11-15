# Build Plan — TaskTimer

**Author:** `creatico6@github.com`

## Goal
Build a simple terminal task manager with live top-bar timers for GNOME, compatible with unprivileged Linux workstations (no `sudo`, no `pip`, using only system Python 3.10 + `python3-gi` + `fish`).

## Architecture
1. **`tasktimer/storage.py`**:
   - Single JSON store at `~/.local/share/tasktimer/tasks.json` with atomic writes (`mkstemp` + `os.replace`).
   - Single-active-task rule: starting another task automatically pauses the currently `"running"` task and flushes its elapsed time.
   - Epoch-based (`started_at`) calculation to prevent clock drift.
2. **`tasktimer/indicator.py`**:
   - GTK 3 daemon with a 1-second `GLib.timeout_add_seconds` tick.
   - Uses `AyatanaAppIndicator3` when `ubuntu-appindicators@ubuntu.com` is enabled, and falls back to `TaskTimerFloatingPill` (always-on-top draggable GTK3 pill) when it is not.
   - Single-instance PID lock in `$XDG_RUNTIME_DIR/tasktimer-indicator.pid`.
   - Menu is rebuilt only when the task list/status signature changes, preventing flicker while open.
3. **`tasktimer/cli.py` & `bin/tasktimer`**:
   - Interactive menu and direct subcommands, plus `--startup` to ensure the background indicator is running.
4. **Fish Integration (`~/.config/fish/conf.d/tasktimer.fish`)**:
   - Uses a marker file in `$XDG_RUNTIME_DIR` (automatically cleared on logout/reboot) to prompt `[Y/n]` only on the first interactive terminal opened after login.
