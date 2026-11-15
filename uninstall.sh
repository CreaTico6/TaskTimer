#!/usr/bin/env bash
# Uninstaller for TaskTimer (userspace-only)
set -euo pipefail

RUNTIME_DIR="${XDG_RUNTIME_DIR:-/tmp}"
PID_FILE="$RUNTIME_DIR/tasktimer-indicator.pid"
MARKER_FILE="$RUNTIME_DIR/tasktimer_session_prompted_$(id -u)"
DATA_DIR="${XDG_DATA_HOME:-$HOME/.local/share}/tasktimer"
REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "Uninstalling TaskTimer..."

# 1. Stop running indicator
if [ -f "$PID_FILE" ]; then
    PID="$(cat "$PID_FILE" 2>/dev/null || true)"
    if [ -n "$PID" ] && kill -0 "$PID" 2>/dev/null; then
        kill "$PID" 2>/dev/null || true
        echo "  - Stopped indicator (PID $PID)"
    fi
    rm -f "$PID_FILE"
fi

# 2. Remove symlinks and Fish startup hook
rm -f "$HOME/.local/bin/tasktimer" "$HOME/.local/bin/tt"
echo "  - Removed ~/.local/bin/tasktimer and ~/.local/bin/tt"

rm -f "$HOME/.config/fish/conf.d/tasktimer.fish" "$MARKER_FILE"
echo "  - Removed ~/.config/fish/conf.d/tasktimer.fish"

# 2b. Remove GNOME Shell extension
if command -v gnome-extensions >/dev/null 2>&1; then
    gnome-extensions disable tasktimer@creatico6 2>/dev/null || true
fi
rm -rf "$HOME/.local/share/gnome-shell/extensions/tasktimer@creatico6"
echo "  - Removed GNOME Shell extension (tasktimer@creatico6)"

# 3. Optional: remove saved tasks
if [ -d "$DATA_DIR" ]; then
    read -r -p "Remove saved task data in $DATA_DIR? [y/N] " ans_data
    if [[ "$ans_data" =~ ^[Yy]$ ]]; then
        rm -rf "$DATA_DIR"
        echo "  - Removed $DATA_DIR"
    else
        echo "  - Kept $DATA_DIR"
    fi
fi

# 4. Optional: remove repository directory
read -r -p "Remove TaskTimer directory ($REPO_DIR)? [y/N] " ans_repo
if [[ "$ans_repo" =~ ^[Yy]$ ]]; then
    rm -rf "$REPO_DIR"
    echo "  - Removed $REPO_DIR"
else
    echo "  - Kept $REPO_DIR"
fi

echo "Done."
