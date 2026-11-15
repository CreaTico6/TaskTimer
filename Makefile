.DEFAULT_GOAL := install

BIN_DIR := $(HOME)/.local/bin
FISH_CONF_DIR := $(HOME)/.config/fish/conf.d
GNOME_EXT_DIR := $(HOME)/.local/share/gnome-shell/extensions/tasktimer@creatico6
ROOT_DIR := $(CURDIR)

.PHONY: install deps fish gnome-ext test uninstall help

help:
	@printf '%s\n' \
		'TaskTimer Makefile targets:' \
		'  make            Install deps, symlinks, Fish hook, and GNOME extension (default)' \
		'  make install    Same as make' \
		'  make deps       Check GTK3 bindings and install PyGObject in userspace if missing' \
		'  make fish       Install only the Fish startup hook' \
		'  make gnome-ext  Install the GNOME Shell top-bar toggle extension' \
		'  make test       Run the unit test suite' \
		'  make uninstall  Run the interactive uninstaller' \
		'  make help       Show this help message'

deps:
	@if python3 -c "import gi; gi.require_version('Gtk','3.0'); gi.require_version('Gdk','3.0'); from gi.repository import Gtk, Gdk" 2>/dev/null || \
	    /usr/bin/python3 -c "import gi; gi.require_version('Gtk','3.0'); gi.require_version('Gdk','3.0'); from gi.repository import Gtk, Gdk" 2>/dev/null; then \
		echo "GTK3 bindings (python3-gi) already available."; \
	else \
		echo "Installing PyGObject in userspace..."; \
		python3 -m pip install --user PyGObject; \
	fi

install: deps
	@chmod +x "$(ROOT_DIR)/bin/tasktimer" "$(ROOT_DIR)/uninstall.sh"
	@mkdir -p "$(BIN_DIR)"
	@ln -sf "$(ROOT_DIR)/bin/tasktimer" "$(BIN_DIR)/tasktimer"
	@ln -sf "$(ROOT_DIR)/bin/tasktimer" "$(BIN_DIR)/tt"
	@echo "Installed symlinks in $(BIN_DIR): tasktimer, tt"
	@if command -v fish >/dev/null 2>&1; then \
		$(MAKE) --no-print-directory fish; \
	fi
	@if command -v gnome-shell >/dev/null 2>&1; then \
		$(MAKE) --no-print-directory gnome-ext; \
	fi
	@echo "Done. Ensure $(BIN_DIR) is in your PATH, then run: tt --startup"

gnome-ext:
	@mkdir -p "$(dir $(GNOME_EXT_DIR))"
	@ln -sfn "$(ROOT_DIR)/gnome-extension/tasktimer@creatico6" "$(GNOME_EXT_DIR)"
	@if command -v gnome-extensions >/dev/null 2>&1; then \
		gnome-extensions enable tasktimer@creatico6 2>/dev/null || true; \
	fi
	@echo "Installed GNOME Shell extension in $(GNOME_EXT_DIR)"
	@echo "Note: Reload GNOME Shell (Alt+F2 -> r on X11, or re-login) to activate the top-bar button."

fish:
	@mkdir -p "$(FISH_CONF_DIR)"
	@printf '%s\n' \
		'# TaskTimer: prompt only on the first interactive terminal opened after login' \
		'if status is-interactive; and command -sq tasktimer' \
		'    set -l _tt_runtime (set -q XDG_RUNTIME_DIR; and echo $$XDG_RUNTIME_DIR; or echo /tmp)' \
		'    set -l _tt_marker "$$_tt_runtime/tasktimer_session_prompted_"(id -u)' \
		'    if not test -f "$$_tt_marker"' \
		'        touch "$$_tt_marker"' \
		'        echo ""' \
		'        read -l -P "⏱  Open TaskTimer and activate the top-bar indicator? [Y/n] " _tt_ans' \
		'        if test -z "$$_tt_ans"; or string match -qi -r '\''^[sy]$$'\'' -- "$$_tt_ans"' \
		'            tasktimer --startup' \
		'        end' \
		'    end' \
		'end' > "$(FISH_CONF_DIR)/tasktimer.fish"
	@echo "Installed Fish startup hook in $(FISH_CONF_DIR)/tasktimer.fish"

test:
	@python3 -m unittest discover -s "$(ROOT_DIR)/tests" -v

uninstall:
	@"$(ROOT_DIR)/uninstall.sh"
