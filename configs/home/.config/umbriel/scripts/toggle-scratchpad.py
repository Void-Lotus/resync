#!/usr/bin/env python3
import os
import sys
import subprocess
import gi
import cairo

gi.require_version('Gtk', '3.0')
gi.require_version('Gdk', '3.0')
gi.require_version('GtkLayerShell', '0.1')
from gi.repository import Gtk, Gdk, GtkLayerShell

PID_FILE = f"/tmp/umbriel_scratchpad_dimmer_{os.getuid()}.pid"

def get_running_pid():
    if os.path.exists(PID_FILE):
        try:
            with open(PID_FILE, 'r') as f:
                pid = int(f.read().strip())
            os.kill(pid, 0)
            return pid
        except (ValueError, OSError):
            if os.path.exists(PID_FILE):
                os.remove(PID_FILE)
    return None

def kill_dimmer():
    pid = get_running_pid()
    if pid:
        try:
            os.kill(pid, 15)
        except OSError:
            pass
        if os.path.exists(PID_FILE):
            os.remove(PID_FILE)
        return True
    return False

def main():
    if kill_dimmer():
        subprocess.run(["umbriel", "msg", "scratchpad-toggle"])
        sys.exit(0)

    with open(PID_FILE, 'w') as f:
        f.write(str(os.getpid()))

    win = Gtk.Window()
    win.set_title("Scratchpad Backdrop")
    win.set_app_paintable(True)

    screen = win.get_screen()
    visual = screen.get_rgba_visual()
    if visual:
        win.set_visual(visual)

    GtkLayerShell.init_for_window(win)
    GtkLayerShell.set_namespace(win, "noctalia-panel-scratchpad")
    GtkLayerShell.set_layer(win, GtkLayerShell.Layer.TOP)
    GtkLayerShell.set_keyboard_mode(win, GtkLayerShell.KeyboardMode.NONE)

    for edge in [GtkLayerShell.Edge.TOP, GtkLayerShell.Edge.BOTTOM, GtkLayerShell.Edge.LEFT, GtkLayerShell.Edge.RIGHT]:
        GtkLayerShell.set_anchor(win, edge, True)

    GtkLayerShell.set_exclusive_zone(win, -1)

    def on_draw(widget, cr):
        cr.set_source_rgba(0.0, 0.0, 0.0, 0.75)
        cr.set_operator(cairo.OPERATOR_SOURCE)
        cr.paint()
        return False

    def on_button_press(widget, event):
        kill_dimmer()
        subprocess.run(["umbriel", "msg", "scratchpad-toggle"])
        Gtk.main_quit()

    win.connect("draw", on_draw)
    win.add_events(Gdk.EventMask.BUTTON_PRESS_MASK)
    win.connect("button-press-event", on_button_press)

    win.show_all()
    while Gtk.events_pending():
        Gtk.main_iteration()

    subprocess.run(["umbriel", "msg", "scratchpad-toggle"])
    Gtk.main()

if __name__ == '__main__':
    main()
