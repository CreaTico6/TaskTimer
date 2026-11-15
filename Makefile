.DEFAULT_GOAL := install

BIN_DIR := $(HOME)/.local/bin
FISH_CONF_DIR := $(HOME)/.config/fish/conf.d
ROOT_DIR := $(CURDIR)

.PHONY: install fish test uninstall help

help:
	@printf '%s\n' \
		'TaskTimer Makefile targets:' \
		'  make            Install symlinks (~/.local/bin) and Fish startup hook (default)' \
		'  make install    Same as make' \
		'  make fish       Install only the Fish startup hook' \
		'  make test       Run the unit test suite' \
		'  make uninstall  Run the interactive uninstaller' \
		'  make help       Show this help message'

install:
	@chmod +x "$(ROOT_DIR)/bin/tasktimer" "$(ROOT_DIR)/uninstall.sh"
	@mkdir -p "$(BIN_DIR)"
	@ln -sf "$(ROOT_DIR)/bin/tasktimer" "$(BIN_DIR)/tasktimer"
	@ln -sf "$(ROOT_DIR)/bin/tasktimer" "$(BIN_DIR)/tt"
	@echo "Installed symlinks in $(BIN_DIR): tasktimer, tt"
	@if command -v fish >/dev/null 2>&1; then \
		$(MAKE) --no-print-directory fish; \
	fi
	@echo "Done. Ensure $(BIN_DIR) is in your PATH, then run: tt --startup"

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
