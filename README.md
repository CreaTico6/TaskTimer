![TaskTimer](TaskTimer.jpg)

**TaskTimer** by `creatico6@github.com`

A lightweight terminal task manager with a **native GNOME top-bar / floating timer indicator**, built to run **100% in userspace (no `sudo`, no `pip`)** (Ubuntu 22.04 / GNOME + `fish`).

## Features

- **Smart `fish` startup**: On the first interactive terminal opened after login, prompts `[Y/n]` to start TaskTimer and activate the top-bar indicator. Never prompts again in subsequent terminal windows during the same login session.
- **Task Manager**: Create, list, start, pause, extend (`+5m`), and complete tasks with a title, optional description, and allocated duration (`25m`, `1h30m`, `45s`).
- **Top-Bar Indicator**: Displays the active task and live countdown (`▶ Task (24:15)`), with a dropdown menu to pause/resume, switch tasks, add `+5 min`, complete, or open the terminal manager. Automatically falls back to a draggable always-on-top GTK3 pill on GNOME sessions without `ubuntu-appindicators@ubuntu.com`.
- **Overtime Alerts**: Sends a desktop notification (`notify-send`) when allocated time reaches `00:00` and continues tracking overtime (`⚠ Task (+01:10)`).

## Userspace Installation (No `sudo`)

- Symlinks: `~/.local/bin/tasktimer` and `~/.local/bin/tt` → `~/Projects/TaskTimer/bin/tasktimer`
- Fish hook: `~/.config/fish/conf.d/tasktimer.fish`
- Data files: `~/.local/share/tasktimer/tasks.json` (active tasks) and `~/.local/share/tasktimer/history.jsonl` (permanent history log)

## Usage

### Interactive Mode
```fish
tasktimer
# or
tt
```

### Direct Subcommands
```fish
tt add "Study Libft" 45m -d "Review ft_split" --start
tt list
tt pause
tt start 1
tt addtime 1 10m
tt done 1
tt history            # view permanent history
tt indicator status   # start | stop | status
```

## Documentation, Uninstall & Tests

- See [CoderManual.md](CoderManual.md) for the full technical manual, architecture, and reproduction guide.
- See [VersionControl.md](VersionControl.md) for the changelog and [LICENSE](LICENSE) for the MIT License.
- To uninstall, run `~/Projects/TaskTimer/uninstall.sh`.

```fish
python3 -m unittest discover -s ~/Projects/TaskTimer/tests -v
```
