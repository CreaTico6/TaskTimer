"""GNOME top-bar indicator (AyatanaAppIndicator3 or floating GTK3 pill fallback)."""

from __future__ import annotations

import os
import shutil
import signal
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

from tasktimer.storage import (
    TaskStore,
    current_elapsed,
    format_duration,
    get_runtime_dir,
    remaining_seconds,
)


def get_pid_file() -> Path:
    """Return the indicator PID file path."""
    return get_runtime_dir() / "tasktimer-indicator.pid"


def read_indicator_pid() -> int | None:
    """Return the running indicator PID, or None if not active."""
    pid_file = get_pid_file()
    if not pid_file.exists():
        return None
    try:
        pid = int(pid_file.read_text(encoding="utf-8").strip())
        os.kill(pid, 0)
        return pid
    except (ValueError, ProcessLookupError, PermissionError, OSError):
        pid_file.unlink(missing_ok=True)
        return None


def is_indicator_running() -> bool:
    """Check whether the indicator daemon is currently running."""
    return read_indicator_pid() is not None


def stop_indicator() -> bool:
    """Stop the indicator daemon if it is running."""
    pid = read_indicator_pid()
    if pid is None:
        return False
    os.kill(pid, signal.SIGTERM)
    get_pid_file().unlink(missing_ok=True)
    return True


def start_indicator_background() -> tuple[bool, int | None]:
    """Start the indicator in the background if not already running.

    Returns (started_now, pid).
    """
    existing = read_indicator_pid()
    if existing is not None:
        return False, existing

    if not os.environ.get("DISPLAY") and not os.environ.get("WAYLAND_DISPLAY"):
        return False, None

    proc = subprocess.Popen(
        [sys.executable, "-m", "tasktimer.indicator"],
        cwd=str(Path(__file__).resolve().parent.parent),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        start_new_session=True,
    )
    return True, proc.pid


def _has_gnome_appindicator_extension() -> bool:
    """Check if GNOME's AppIndicator extension is enabled in this session."""
    gnome_ext = shutil.which("gnome-extensions")
    if not gnome_ext:
        return False
    try:
        out = subprocess.check_output(
            [gnome_ext, "list", "--enabled"],
            text=True,
            stderr=subprocess.DEVNULL,
            timeout=2,
        )
        return "appindicators" in out.lower()
    except Exception:
        return False


def _truncate(text: str, limit: int = 24) -> str:
    return text if len(text) <= limit else text[: limit - 1] + "…"


def _send_notification(title: str, body: str) -> None:
    notifier = shutil.which("notify-send")
    if not notifier:
        return
    subprocess.Popen(
        [notifier, "-a", "TaskTimer", "-u", "normal", title, body],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


def _open_terminal_manager() -> None:
    tasktimer_bin = shutil.which("tasktimer") or str(Path(__file__).resolve().parent.parent / "bin" / "tasktimer")
    if shutil.which("gnome-terminal"):
        cmd = ["gnome-terminal", "--", tasktimer_bin]
    elif shutil.which("x-terminal-emulator"):
        cmd = ["x-terminal-emulator", "-e", tasktimer_bin]
    else:
        return
    subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)


class _BaseIndicatorController:
    """Shared controller logic for AppIndicator3 and the floating GTK3 pill."""

    def __init__(self, gtk_mod: Any, glib_mod: Any) -> None:
        self.Gtk = gtk_mod
        self.GLib = glib_mod
        self.store = TaskStore()
        self._menu_signature: tuple[Any, ...] | None = None
        self._header_item: Any = None
        self.menu: Any = None

    def _format_top_label(self, active: dict[str, Any] | None) -> str:
        if active is None:
            return "⏱ TiSoft TaskTimer"
        rem = remaining_seconds(active)
        title = _truncate(active["title"], 22)
        if active["status"] == "running":
            if rem >= 0:
                return f"▶ {title} ({format_duration(rem)})"
            return f"⚠ {title} ({format_duration(rem, show_sign=True)})"
        return f"⏸ {title} ({format_duration(rem, show_sign=True)})"

    def _format_header_text(self, active: dict[str, Any] | None) -> str:
        if active is None:
            return "No active task"
        rem = remaining_seconds(active)
        alloc = format_duration(int(active["allocated_seconds"]))
        rem_txt = format_duration(rem, show_sign=True)
        state = "Running" if active["status"] == "running" else "Paused"
        desc = f" — {_truncate(active['description'], 36)}" if active.get("description") else ""
        return f"#{active['id']} {active['title']}{desc} | {state}: {rem_txt} / {alloc}"

    def _check_overtime_notification(self, active: dict[str, Any] | None) -> None:
        if active is None or active["status"] != "running":
            return
        if remaining_seconds(active) <= 0 and not active.get("notified_overtime"):
            self.store.mark_notified_overtime(int(active["id"]))
            _send_notification(
                "⏱ Allocated time finished!",
                f"Task '{active['title']}' reached its time limit. Counting overtime.",
            )

    def _set_bold_item_text(self, item: Any, text: str) -> None:
        child = item.get_child()
        if child is not None:
            child.get_style_context().add_class("tasktimer-menu-header")
            child.set_markup(f"<b>{self.GLib.markup_escape_text(text)}</b>")

    def _add_item(
        self,
        menu: Any,
        label: str,
        callback: Any = None,
        sensitive: bool = True,
        bold: bool = False,
        section: bool = False,
    ) -> Any:
        item = self.Gtk.MenuItem(label=label)
        item.set_sensitive(sensitive)
        if section:
            item.get_style_context().add_class("tasktimer-menu-section")
        if bold:
            self._set_bold_item_text(item, label)
        if callback is not None:
            item.connect("activate", callback)
        menu.append(item)
        return item

    def _rebuild_menu(self, tasks: list[dict[str, Any]], active: dict[str, Any] | None) -> Any:
        menu = self.Gtk.Menu()
        self._header_item = self._add_item(
            menu, self._format_header_text(active), sensitive=False, bold=True, section=True
        )
        menu.append(self.Gtk.SeparatorMenuItem())

        if active is not None:
            toggle_label = "⏸ Pause" if active["status"] == "running" else "▶ Resume"
            self._add_item(menu, toggle_label, lambda _w: self._action(self.store.toggle_active), section=True)
            self._add_item(
                menu, "✔ Complete current task", lambda _w: self._action(self.store.complete_task), section=True
            )
            self._add_item(
                menu,
                "➕ Add +5 min",
                lambda _w, tid=int(active["id"]): self._action(lambda: self.store.add_time(tid, 300)),
                section=True,
            )
            menu.append(self.Gtk.SeparatorMenuItem())

        other_tasks = [t for t in tasks if active is None or int(t["id"]) != int(active["id"])]
        if other_tasks:
            self._add_item(menu, "Switch / Start task:", sensitive=False, bold=True, section=False)
            for task in other_tasks[:10]:
                rem = format_duration(remaining_seconds(task), show_sign=True)
                label = f"  ▶ #{task['id']} {_truncate(task['title'], 28)} ({rem})"
                self._add_item(
                    menu,
                    label,
                    lambda _w, tid=int(task["id"]): self._action(lambda: self.store.start_task(tid)),
                )
            menu.append(self.Gtk.SeparatorMenuItem())

        self._add_item(menu, "🖥 Open Terminal Manager", lambda _w: _open_terminal_manager())
        self._add_item(menu, "❌ Close Indicator", lambda _w: self.quit())
        menu.show_all()
        self.menu = menu
        return menu

    def _refresh(self, force_menu: bool = False) -> None:
        tasks = self.store.list_tasks(include_done=False)
        active = self.store.get_active_task()
        self._check_overtime_notification(active)

        self._apply_label(self._format_top_label(active), active, tasks)
        signature = tuple((t["id"], t["status"], t["title"], t["allocated_seconds"]) for t in tasks)
        if force_menu or signature != self._menu_signature:
            self._menu_signature = signature
            menu = self._rebuild_menu(tasks, active)
            self._apply_menu(menu)
        elif self._header_item is not None:
            self._set_bold_item_text(self._header_item, self._format_header_text(active))

    def _apply_label(self, text: str, active: dict[str, Any] | None, tasks: list[dict[str, Any]]) -> None:
        raise NotImplementedError

    def _apply_menu(self, menu: Any) -> None:
        raise NotImplementedError

    def _action(self, fn: Any) -> None:
        fn()
        self._refresh(force_menu=True)

    def _on_tick(self) -> bool:
        self._refresh(force_menu=False)
        return True

    def quit(self) -> None:
        get_pid_file().unlink(missing_ok=True)
        self.Gtk.main_quit()

    def run(self) -> None:
        self._refresh(force_menu=True)
        self.GLib.timeout_add_seconds(1, self._on_tick)
        self.Gtk.main()


class TaskTimerAppIndicator(_BaseIndicatorController):
    """Native AppIndicator3 mode (when the GNOME extension is active)."""

    def __init__(self, gtk_mod: Any, glib_mod: Any, appind_mod: Any) -> None:
        super().__init__(gtk_mod, glib_mod)
        self.indicator = appind_mod.Indicator.new(
            "tasktimer-indicator",
            "alarm-symbolic",
            appind_mod.IndicatorCategory.APPLICATION_STATUS,
        )
        self.indicator.set_status(appind_mod.IndicatorStatus.ACTIVE)
        self.indicator.set_title("TaskTimer")

    def _apply_label(self, text: str, active: dict[str, Any] | None, tasks: list[dict[str, Any]]) -> None:
        self.indicator.set_label(f" {text}", "")

    def _apply_menu(self, menu: Any) -> None:
        self.indicator.set_menu(menu)


class TaskTimerCardPopup:
    """Sleek dark GTK3 card popup with progress bar, action buttons, and task switcher."""

    def __init__(self, controller: TaskTimerFloatingPill) -> None:
        self.ctrl = controller
        self.Gtk = controller.Gtk
        self.Gdk = controller.Gdk
        self._card_signature: tuple[Any, ...] | None = None
        self._last_focus_out = 0.0
        self._time_label: Any = None
        self._progress_bar: Any = None

        self.popup = self.Gtk.Window(type=self.Gtk.WindowType.TOPLEVEL)
        self.popup.set_title("TiSoft TaskTimer")
        self.popup.set_decorated(False)
        self.popup.set_keep_above(True)
        self.popup.set_skip_taskbar_hint(True)
        self.popup.set_skip_pager_hint(True)
        self.popup.set_resizable(False)
        self.popup.stick()
        self.popup.set_type_hint(self.Gdk.WindowTypeHint.POPUP_MENU)
        self.popup.get_style_context().add_class("tasktimer-card")

        self.popup.connect("focus-out-event", self._on_focus_out)
        self.popup.connect("key-press-event", self._on_key_press)

        self.root_box = self.Gtk.Box(orientation=self.Gtk.Orientation.VERTICAL, spacing=10)
        self.popup.add(self.root_box)

    def _on_focus_out(self, _widget: Any, _event: Any) -> bool:
        self._last_focus_out = time.monotonic()
        self.hide()
        return False

    def _on_key_press(self, _widget: Any, event: Any) -> bool:
        if event.keyval == self.Gdk.KEY_Escape:
            self.hide()
            return True
        return False

    def is_visible(self) -> bool:
        return bool(self.popup.get_visible())

    def hide(self) -> None:
        if self.popup.get_visible():
            self.popup.hide()

    def toggle(self, anchor_window: Any) -> None:
        if self.popup.get_visible() or (time.monotonic() - self._last_focus_out) < 0.18:
            self.hide()
            return
        self.update(force=True)
        self.popup.show_all()
        self._position_near(anchor_window)
        self.popup.present()

    def _position_near(self, anchor_window: Any) -> None:
        display = self.Gdk.Display.get_default()
        if display is None:
            return
        ax, ay = anchor_window.get_position()
        aw, ah = anchor_window.get_size()
        pw, ph = self.popup.get_size()
        monitor = display.get_monitor_at_point(ax, ay) or display.get_primary_monitor() or display.get_monitor(0)
        work = monitor.get_workarea()

        x = min(max(work.x + 8, ax + aw - pw), work.x + work.width - pw - 8)
        y = ay + ah + 6
        if y + ph > work.y + work.height - 8:
            y = max(work.y + 8, ay - ph - 6)
        self.popup.move(x, y)

    def _make_button(self, label: str, css_class: str, callback: Any) -> Any:
        btn = self.Gtk.Button(label=label)
        btn.get_style_context().add_class(css_class)
        btn.set_relief(self.Gtk.ReliefStyle.NONE)
        btn.connect("clicked", lambda _b: callback())
        return btn

    def _active_time_text(self, active: dict[str, Any]) -> tuple[str, float, bool]:
        rem = remaining_seconds(active)
        alloc = int(active["allocated_seconds"])
        elapsed = current_elapsed(active)
        ratio = min(1.0, max(0.0, elapsed / max(1, alloc)))
        state = "Running" if active["status"] == "running" else "Paused"
        if rem >= 0:
            text = f"{state} • {format_duration(rem)} left / {format_duration(alloc)}"
        else:
            text = f"Overtime • {format_duration(rem, show_sign=True)} / {format_duration(alloc)}"
        return text, ratio, (active["status"] == "running" and rem < 0)

    def _rebuild(self, tasks: list[dict[str, Any]], active: dict[str, Any] | None) -> None:
        for child in self.root_box.get_children():
            self.root_box.remove(child)
        self._time_label = None
        self._progress_bar = None

        # Active task card section
        active_box = self.Gtk.Box(orientation=self.Gtk.Orientation.VERTICAL, spacing=6)
        active_box.get_style_context().add_class("tasktimer-active-card")

        if active is not None:
            title_lbl = self.Gtk.Label(label=f"#{active['id']}  {active['title']}")
            title_lbl.get_style_context().add_class("tasktimer-card-title")
            title_lbl.set_xalign(0.0)
            title_lbl.set_line_wrap(True)
            title_lbl.set_max_width_chars(34)
            active_box.pack_start(title_lbl, False, False, 0)

            if active.get("description"):
                desc_lbl = self.Gtk.Label(label=active["description"])
                desc_lbl.get_style_context().add_class("tasktimer-card-desc")
                desc_lbl.set_xalign(0.0)
                desc_lbl.set_line_wrap(True)
                desc_lbl.set_max_width_chars(38)
                active_box.pack_start(desc_lbl, False, False, 0)

            time_txt, ratio, is_overtime = self._active_time_text(active)
            self._time_label = self.Gtk.Label(label=time_txt)
            self._time_label.get_style_context().add_class("tasktimer-card-time")
            if is_overtime:
                self._time_label.get_style_context().add_class("overtime")
            self._time_label.set_xalign(0.0)
            active_box.pack_start(self._time_label, False, False, 0)

            self._progress_bar = self.Gtk.ProgressBar()
            self._progress_bar.get_style_context().add_class("tasktimer-progress")
            self._progress_bar.set_fraction(ratio)
            active_box.pack_start(self._progress_bar, False, False, 2)

            btn_row = self.Gtk.Box(orientation=self.Gtk.Orientation.HORIZONTAL, spacing=6)
            toggle_lbl = "⏸ Pause" if active["status"] == "running" else "▶ Resume"
            btn_row.pack_start(
                self._make_button(toggle_lbl, "tasktimer-btn", lambda: self.ctrl._action(self.ctrl.store.toggle_active)),
                True,
                True,
                0,
            )
            btn_row.pack_start(
                self._make_button("✔ Done", "tasktimer-btn", lambda: self.ctrl._action(self.ctrl.store.complete_task)),
                True,
                True,
                0,
            )
            tid = int(active["id"])
            btn_row.pack_start(
                self._make_button("➕ +5m", "tasktimer-btn", lambda t=tid: self.ctrl._action(lambda: self.ctrl.store.add_time(t, 300))),
                True,
                True,
                0,
            )
            active_box.pack_start(btn_row, False, False, 2)
        else:
            empty_lbl = self.Gtk.Label(label="No active task")
            empty_lbl.get_style_context().add_class("tasktimer-card-desc")
            empty_lbl.set_xalign(0.0)
            active_box.pack_start(empty_lbl, False, False, 0)

        self.root_box.pack_start(active_box, False, False, 0)

        # Switch / Start task section
        other_tasks = [t for t in tasks if active is None or int(t["id"]) != int(active["id"])]
        if other_tasks:
            sec_lbl = self.Gtk.Label(label="SWITCH / START TASK")
            sec_lbl.get_style_context().add_class("tasktimer-section-title")
            sec_lbl.set_xalign(0.0)
            self.root_box.pack_start(sec_lbl, False, False, 0)

            list_box = self.Gtk.Box(orientation=self.Gtk.Orientation.VERTICAL, spacing=4)
            for task in other_tasks[:8]:
                tid = int(task["id"])
                rem = format_duration(remaining_seconds(task), show_sign=True)
                btn = self._make_button(
                    f"▶  #{tid} {_truncate(task['title'], 24)}   ({rem})",
                    "tasktimer-switch-btn",
                    lambda t=tid: self.ctrl._action(lambda: self.ctrl.store.start_task(t)),
                )
                child = btn.get_child()
                if child is not None:
                    child.set_xalign(0.0)
                list_box.pack_start(btn, False, False, 0)
            self.root_box.pack_start(list_box, False, False, 0)

        # Footer button
        footer = self.Gtk.Box(orientation=self.Gtk.Orientation.HORIZONTAL, spacing=6)
        footer.pack_start(
            self._make_button("🖥 Terminal", "tasktimer-footer-btn", self._open_terminal_and_hide),
            True,
            True,
            0,
        )
        self.root_box.pack_start(footer, False, False, 0)
        self.root_box.show_all()
        self.popup.resize(1, 1)

    def _open_terminal_and_hide(self) -> None:
        self.hide()
        _open_terminal_manager()

    def update(self, force: bool = False) -> None:
        if not force and not self.popup.get_visible():
            return
        tasks = self.ctrl.store.list_tasks(include_done=False)
        active = self.ctrl.store.get_active_task()
        signature = tuple((t["id"], t["status"], t["title"], t.get("description", ""), t["allocated_seconds"]) for t in tasks)
        if force or signature != self._card_signature:
            self._card_signature = signature
            self._rebuild(tasks, active)
        elif active is not None and self._time_label is not None and self._progress_bar is not None:
            time_txt, ratio, is_overtime = self._active_time_text(active)
            self._time_label.set_text(time_txt)
            ctx = self._time_label.get_style_context()
            if is_overtime:
                ctx.add_class("overtime")
            else:
                ctx.remove_class("overtime")
            self._progress_bar.set_fraction(ratio)


class TaskTimerFloatingPill(_BaseIndicatorController):
    """Always-on-top floating GTK3 pill (fallback when no GNOME tray extension is active)."""

    def __init__(self, gtk_mod: Any, gdk_mod: Any, glib_mod: Any) -> None:
        super().__init__(gtk_mod, glib_mod)
        self.Gdk = gdk_mod
        self._drag_origin: tuple[float, float] | None = None
        self._win_origin: tuple[int, int] | None = None
        self._was_dragged = False
        self._positioned = False

        self.window = gtk_mod.Window(type=gtk_mod.WindowType.TOPLEVEL)
        self.window.set_title("TiSoft TaskTimer")
        self.window.set_decorated(False)
        self.window.set_keep_above(True)
        self.window.set_accept_focus(False)
        self.window.set_skip_taskbar_hint(True)
        self.window.set_skip_pager_hint(True)
        self.window.set_resizable(False)
        self.window.stick()
        self.window.set_type_hint(gdk_mod.WindowTypeHint.UTILITY)

        css = gtk_mod.CssProvider()
        css.load_from_data(
            b"""
            window.tasktimer-pill {
                background-color: #1e222a;
                border: 1px solid #4c566a;
                border-radius: 12px;
            }
            window.tasktimer-pill.overtime {
                background-color: #4c1d24;
                border-color: #bf616a;
            }
            label.tasktimer-brand {
                color: #88c0d0;
                font-weight: bold;
                font-size: 10px;
                padding: 4px 12px 0px 12px;
            }
            label.tasktimer-text {
                color: #eceff4;
                font-weight: bold;
                font-size: 13px;
                padding: 0px 12px 5px 12px;
            }
            window.tasktimer-card {
                background-color: #1e222a;
                border: 1px solid #4c566a;
                border-radius: 12px;
                padding: 12px;
                min-width: 280px;
            }
            .tasktimer-active-card {
                background-color: #252a34;
                border-left: 3px solid #88c0d0;
                border-radius: 8px;
                padding: 10px;
            }
            label.tasktimer-card-title {
                color: #eceff4;
                font-weight: bold;
                font-size: 13px;
            }
            label.tasktimer-card-desc {
                color: #9aa5b1;
                font-size: 11px;
            }
            label.tasktimer-card-time {
                color: #88c0d0;
                font-weight: bold;
                font-size: 12px;
            }
            label.tasktimer-card-time.overtime {
                color: #bf616a;
            }
            progressbar.tasktimer-progress trough {
                background-color: #3b4252;
                border-radius: 4px;
                min-height: 6px;
            }
            progressbar.tasktimer-progress progress {
                background-color: #88c0d0;
                border-radius: 4px;
                min-height: 6px;
            }
            label.tasktimer-section-title {
                color: #88c0d0;
                font-weight: bold;
                font-size: 10px;
                padding-left: 2px;
            }
            button.tasktimer-btn {
                background-color: #2e3440;
                color: #eceff4;
                border: 1px solid #4c566a;
                border-radius: 6px;
                padding: 5px 8px;
                font-size: 12px;
                font-weight: bold;
            }
            button.tasktimer-btn:hover {
                background-color: #3b4252;
                border-color: #88c0d0;
            }
            button.tasktimer-switch-btn {
                background-color: #252a34;
                color: #d8dee9;
                border: 1px solid #3b4252;
                border-radius: 6px;
                padding: 5px 8px;
                font-size: 12px;
            }
            button.tasktimer-switch-btn:hover {
                background-color: #3b4252;
                border-color: #88c0d0;
                color: #eceff4;
            }
            button.tasktimer-footer-btn {
                background-color: transparent;
                color: #9aa5b1;
                border: 1px solid #3b4252;
                border-radius: 6px;
                padding: 4px 8px;
                font-size: 11px;
            }
            button.tasktimer-footer-btn:hover {
                background-color: #2e3440;
                color: #eceff4;
            }
            """
        )
        gtk_mod.StyleContext.add_provider_for_screen(
            gdk_mod.Screen.get_default(),
            css,
            gtk_mod.STYLE_PROVIDER_PRIORITY_APPLICATION,
        )
        self.window.get_style_context().add_class("tasktimer-pill")

        self.event_box = gtk_mod.EventBox()
        self.event_box.add_events(
            gdk_mod.EventMask.BUTTON_PRESS_MASK
            | gdk_mod.EventMask.BUTTON_RELEASE_MASK
            | gdk_mod.EventMask.POINTER_MOTION_MASK
        )
        self.event_box.connect("button-press-event", self._on_button_press)
        self.event_box.connect("motion-notify-event", self._on_motion)
        self.event_box.connect("button-release-event", self._on_button_release)

        box = gtk_mod.Box(orientation=gtk_mod.Orientation.VERTICAL, spacing=2)
        self.brand_label = gtk_mod.Label(label="⏱ TiSoft TaskTimer")
        self.brand_label.get_style_context().add_class("tasktimer-brand")
        self.brand_label.set_xalign(0.0)
        box.pack_start(self.brand_label, False, False, 0)

        self.tasks_box = gtk_mod.Box(orientation=gtk_mod.Orientation.VERTICAL, spacing=2)
        self._task_labels: list[Any] = []
        box.pack_start(self.tasks_box, False, False, 0)

        self.event_box.add(box)
        self.window.add(self.event_box)
        self.card_popup = TaskTimerCardPopup(self)
        self.window.show_all()

    @staticmethod
    def _format_task_line(task: dict[str, Any]) -> str:
        rem = remaining_seconds(task)
        title = _truncate(task["title"], 22)
        status = task["status"]
        if status == "running":
            icon = "⚠" if rem < 0 else "▶"
        elif status == "paused":
            icon = "⏸"
        else:
            icon = "•"
        return f"{icon} {title} ({format_duration(rem, show_sign=True)})"

    def _sync_task_label_count(self, count: int) -> None:
        if len(self._task_labels) == count:
            return
        for child in self._task_labels:
            self.tasks_box.remove(child)
        self._task_labels = []
        for _ in range(count):
            lbl = self.Gtk.Label()
            lbl.get_style_context().add_class("tasktimer-text")
            lbl.set_xalign(0.0)
            self.tasks_box.pack_start(lbl, False, False, 0)
            self._task_labels.append(lbl)
        self.tasks_box.show_all()
        self.window.resize(1, 1)

    def _position_top_right(self) -> None:
        display = self.Gdk.Display.get_default()
        if display is None:
            return
        monitor = display.get_primary_monitor() or display.get_monitor(0)
        if monitor is None:
            return
        work = monitor.get_workarea()
        width, _ = self.window.get_size()
        x = max(work.x + 8, work.x + work.width - max(width, 160) - 16)
        y = work.y + 4
        self.window.move(x, y)
        self._positioned = True

    def _apply_label(self, text: str, active: dict[str, Any] | None, tasks: list[dict[str, Any]]) -> None:
        visible_tasks = tasks[:3]
        lines = [self._format_task_line(t) for t in visible_tasks] if visible_tasks else ["No active task"]
        self._sync_task_label_count(len(lines))
        for lbl, line in zip(self._task_labels, lines):
            lbl.set_text(line)

        ctx = self.window.get_style_context()
        if active is not None and active["status"] == "running" and remaining_seconds(active) < 0:
            ctx.add_class("overtime")
        else:
            ctx.remove_class("overtime")
        if not self._positioned:
            self._position_top_right()
        self.card_popup.update(force=False)

    def _apply_menu(self, menu: Any) -> None:
        self.menu = menu

    def _on_button_press(self, _widget: Any, event: Any) -> bool:
        if event.button == 1:
            self._drag_origin = (event.x_root, event.y_root)
            self._win_origin = self.window.get_position()
            self._was_dragged = False
            return True
        if event.button == 3:
            self.card_popup.toggle(self.window)
            return True
        return False

    def _on_motion(self, _widget: Any, event: Any) -> bool:
        if self._drag_origin is None or self._win_origin is None:
            return False
        dx = event.x_root - self._drag_origin[0]
        dy = event.y_root - self._drag_origin[1]
        if abs(dx) > 4 or abs(dy) > 4:
            self._was_dragged = True
            self.window.move(int(self._win_origin[0] + dx), int(self._win_origin[1] + dy))
        return True

    def _on_button_release(self, _widget: Any, event: Any) -> bool:
        if event.button == 1:
            was_dragged = self._was_dragged
            self._drag_origin = None
            self._win_origin = None
            self._was_dragged = False
            if not was_dragged:
                self.card_popup.toggle(self.window)
            return True
        return False


def _create_controller() -> _BaseIndicatorController:
    import gi

    gi.require_version("Gtk", "3.0")
    gi.require_version("Gdk", "3.0")
    from gi.repository import Gdk, GLib, Gtk

    if _has_gnome_appindicator_extension():
        try:
            gi.require_version("AyatanaAppIndicator3", "0.1")
            from gi.repository import AyatanaAppIndicator3

            return TaskTimerAppIndicator(Gtk, GLib, AyatanaAppIndicator3)
        except Exception:
            pass

    return TaskTimerFloatingPill(Gtk, Gdk, GLib)


def main() -> int:
    """Start the indicator process if it is not already running."""
    if is_indicator_running():
        return 0

    pid_file = get_pid_file()
    pid_file.parent.mkdir(parents=True, exist_ok=True)
    pid_file.write_text(str(os.getpid()), encoding="utf-8")

    app = _create_controller()
    signal.signal(signal.SIGTERM, lambda _s, _f: app.quit())
    signal.signal(signal.SIGINT, lambda _s, _f: app.quit())
    try:
        app.run()
    finally:
        pid_file.unlink(missing_ok=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
