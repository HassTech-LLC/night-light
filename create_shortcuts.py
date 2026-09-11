"""
Windows Shortcut and Taskbar Pinning Helper for Night Light.
Uses Windows Script Host (WScript.Shell) or PowerShell COM object to create .lnk shortcuts.
"""

import os
from pathlib import Path
import subprocess
import sys
import base64


def create_shortcut(
    target_path: Path,
    shortcut_path: Path,
    icon_path: Path,
    description: str = "Night Light",
    arguments: str = "",
    working_dir: Path = None,
):
    """Creates a Windows .lnk shortcut using PowerShell COM object."""
    if working_dir is None:
        working_dir = target_path.parent

    # Pass data as base64 rather than interpolating paths into PowerShell.
    # This handles apostrophes, smart quotes and shell metacharacters.
    def encoded(value: str) -> str:
        return base64.b64encode(str(value).encode("utf-8")).decode("ascii")

    safe_target = encoded(target_path)
    safe_shortcut = encoded(shortcut_path)
    safe_icon = encoded(icon_path)
    safe_work = encoded(working_dir)
    safe_args = encoded(arguments)
    safe_desc = encoded(description)

    ps_script = f"""
$utf8 = [System.Text.Encoding]::UTF8
$decode = {{ param($v) $utf8.GetString([Convert]::FromBase64String($v)) }}
$ws = New-Object -ComObject WScript.Shell
$s = $ws.CreateShortcut((&$decode '{safe_shortcut}'))
$s.TargetPath = &$decode '{safe_target}'
$s.Arguments = &$decode '{safe_args}'
$s.WorkingDirectory = &$decode '{safe_work}'
$s.IconLocation = &$decode '{safe_icon}'
$s.Description = &$decode '{safe_desc}'
$s.Save()
"""
    subprocess.run(["powershell", "-NoProfile", "-Command", ps_script], check=True)


def create_all_shortcuts():
    project_dir = Path(__file__).parent.resolve()
    assets_dir = project_dir / "assets"
    ico_path = assets_dir / "app.ico"

    if getattr(sys,"frozen",False):
        # __file__ may belong to PyInstaller's temporary extraction directory.
        # The installed executable is the durable identity and embeds its icon.
        target = Path(sys.executable).resolve()
        ico_path = target
        working_dir = target.parent
        show_args = "--show"
        toggle_args = "--toggle"
    else:
        python_exe = Path(sys.executable)
        pythonw_exe = python_exe.parent / "pythonw.exe"
        if not pythonw_exe.exists():
            pythonw_exe = python_exe

        target = pythonw_exe
        show_args = f'"{project_dir / "main.py"}" --show'
        toggle_args = f'"{project_dir / "main.py"}" --toggle'
        working_dir = project_dir

    # 1. Desktop Shortcut
    desktop = Path(os.environ.get("USERPROFILE", "")) / "Desktop"
    if desktop.exists():
        desktop_shortcut = desktop / "Night Light.lnk"
        create_shortcut(
            target_path=target,
            shortcut_path=desktop_shortcut,
            icon_path=ico_path,
            description="Open Night Light controls and Smart schedule",
            arguments=show_args,
            working_dir=working_dir,
        )
        print(f"[Shortcuts] Created Desktop shortcut at: {desktop_shortcut}")

    # 2. The primary Start entry is the pin-capable one-click moon. Controls
    # remain a separate explicit action so opening settings never toggles.
    appdata = Path(os.environ.get("APPDATA", ""))
    start_menu = appdata / "Microsoft" / "Windows" / "Start Menu" / "Programs"
    if start_menu.exists():
        start_shortcut = start_menu / "Night Light.lnk"
        create_shortcut(
            target_path=target,
            shortcut_path=start_shortcut,
            icon_path=ico_path,
            description="Turn Night Light on or off",
            arguments=toggle_args,
            working_dir=working_dir,
        )
        print(f"[Shortcuts] Created Start Menu shortcut at: {start_shortcut}")
        controls_shortcut = start_menu / "Night Light Controls.lnk"
        create_shortcut(
            target_path=target,
            shortcut_path=controls_shortcut,
            icon_path=ico_path,
            description="Open Night Light controls and Smart schedule",
            arguments=show_args,
            working_dir=working_dir,
        )
        print(f"[Shortcuts] Created controls shortcut at: {controls_shortcut}")

    # Windows does not provide a supported API for pinning automatically. If
    # the user already pinned Night Light, keep that moon as the instant toggle.
    taskbar = appdata / "Microsoft" / "Internet Explorer" / "Quick Launch" / "User Pinned" / "TaskBar"
    for name in ("Night Light.lnk", "Night Light by HT.lnk"):
        pinned = taskbar / name
        if pinned.exists():
            create_shortcut(
                target_path=target,
                shortcut_path=pinned,
                icon_path=ico_path,
                description="Turn Night Light on or off",
                arguments=toggle_args,
                working_dir=working_dir,
            )
            print(f"[Shortcuts] Updated pinned toggle at: {pinned}")


if __name__ == "__main__":
    create_all_shortcuts()
