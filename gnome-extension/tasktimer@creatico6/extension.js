/* TiSoft TaskTimer GNOME Shell Extension (GNOME 42–44) */
const { Gio, GLib, St } = imports.gi;
const Main = imports.ui.main;
const PanelMenu = imports.ui.panelMenu;

let _button = null;

function _toggleTaskTimer() {
    const ttBin = GLib.build_filenamev([GLib.get_home_dir(), '.local', 'bin', 'tt']);
    try {
        Gio.Subprocess.new(
            [ttBin, 'indicator', 'toggle'],
            Gio.SubprocessFlags.NONE
        );
    } catch (e) {
        logError(e, 'TiSoft TaskTimer: failed to toggle indicator');
    }
}

function init() {}

function enable() {
    _button = new PanelMenu.Button(0.0, 'TiSoft TaskTimer', true);
    const label = new St.Label({
        text: '⏱',
        y_align: imports.gi.Clutter.ActorAlign.CENTER,
        style: 'font-size: 14px; padding: 0 4px;',
    });
    _button.add_child(label);
    _button.connect('button-press-event', () => {
        _toggleTaskTimer();
        return imports.gi.Clutter.EVENT_STOP;
    });
    Main.panel.addToStatusArea('tisoft-tasktimer', _button);
}

function disable() {
    if (_button) {
        _button.destroy();
        _button = null;
    }
}
