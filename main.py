"""
Main entry point for Night Light.
Handles single-instance dispatch, CLI flags, and starting the Tray application.
"""

import sys
import os
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.resolve()))

from ipc_transport import send_ipc_command
from create_shortcuts import create_all_shortcuts


def command_from_args(args):
    """Translate CLI arguments into an application command."""
    args = list(args)
    if "--shortcut" in args or "--install-shortcut" in args:
        return "SHORTCUT"
    if "--background" in args:
        return "START"
    if "--show" in args or "--adjust" in args or "--open" in args:
        return "SHOW"
    if "--toggle" in args:
        return "TOGGLE"
    if "--preset" in args:
        try:
            return f"PRESET {args[args.index('--preset') + 1]}"
        except (IndexError, ValueError):
            return "PRESET 6500"
    if "--strength" in args:
        try:
            strength = int(args[args.index('--strength') + 1])
        except (IndexError, ValueError):
            strength = 0
        return f"STRENGTH {max(0, min(100, strength))}"
    if "--windows-off" in args:
        return "WINDOWS_OFF"
    return "TOGGLE"


def main():
    args = sys.argv[1:]
    command = command_from_args(args)
    if command == "SHORTCUT":
        create_all_shortcuts()
        print("Created Night Light shortcuts successfully!")
        return

    from ipc_transport import reserve_listener
    try:
        listener = reserve_listener()
    except OSError:
        # This process is a client for its entire lifetime, even if the peer
        # disappears or denies authentication. Never retry as a resident.
        if send_ipc_command(command):
            raise SystemExit(0)
        raise SystemExit("Night Light is already running or its local endpoint is unavailable.")
    try:
        # No display initialization or exit-reset registration before ownership.
        from tray_app import TrayApp
        app = TrayApp(listener)
    except BaseException:
        listener.close()
        raise
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
