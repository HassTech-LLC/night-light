"""
Main entry point for Night Light by HT.
Handles single-instance dispatch, CLI flags, and starting the Tray application.
"""

import sys
import os
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.resolve()))

from tray_app import TrayApp, send_ipc_command
from create_shortcuts import create_all_shortcuts


def main():
    args = sys.argv[1:]

    if "--shortcut" in args or "--install-shortcut" in args:
        create_all_shortcuts()
        print("Created Night Light by HT shortcuts successfully!")
        return

    command = "TOGGLE"
    if "--background" in args:
        command = "START"
    elif "--show" in args or "--adjust" in args or "--open" in args:
        command = "SHOW"
    elif "--toggle" in args:
        command = "TOGGLE"
    elif "--preset" in args:
        try:
            idx = args.index("--preset")
            if idx + 1 < len(args):
                command = f"PRESET {args[idx+1]}"
        except Exception:
            pass
    elif "--strength" in args:
        try:
            idx = args.index("--strength")
            strength = int(args[idx + 1])
            command = f"STRENGTH {max(0, min(100, strength))}"
        except (IndexError, ValueError):
            pass
    elif "--windows-off" in args:
        command = "WINDOWS_OFF"

    # If instance already running, send IPC command and exit immediately
    if send_ipc_command(command):
        sys.exit(0)

    # First instance startup
    app = TrayApp()
    if command == "SHOW":
        app.root.after(150, app.show_flyout)
    elif command.startswith("PRESET"):
        try:
            k = int(command.split()[1])
            app.root.after(150, lambda k=k: app.apply_preset(k))
        except Exception:
            pass
    elif command.startswith("STRENGTH"):
        try:
            strength = int(command.split()[1])
            app.root.after(150, lambda strength=strength: app.apply_strength(strength))
        except Exception:
            pass
    elif command == "WINDOWS_OFF":
        app.root.after(150, app.turn_windows_nightlight_off)
    elif command == "TOGGLE":
        app.root.after(150, lambda: app.toggle_nightlight(show_hud=True))

    app.run()


if __name__ == "__main__":
    main()
