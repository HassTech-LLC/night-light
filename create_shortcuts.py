"""
Windows Shortcut and Taskbar Pinning Helper for Night Light by HT.
Uses Windows Script Host (WScript.Shell) or PowerShell COM object to create .lnk shortcuts.
"""

import os
from pathlib import Path
import subprocess
import sys


def create_shortcut(
    target_path: Path,
    shortcut_path: Path,
    icon_path: Path,
    description: str = "Night Light by HT",
    arguments: str = "",
    working_dir: Path = None,
):
    """Creates a Windows .lnk shortcut using PowerShell COM object."""
    if working_dir is None:
        working_dir = target_path.parent

    # Escape backslashes and quotes for PowerShell string literal
    safe_target = str(target_path).replace("'", "''")
    safe_shortcut = str(shortcut_path).replace("'", "''")
    safe_icon = str(icon_path).replace("'", "''")
    safe_work = str(working_dir).replace("'", "''")
    safe_args = str(arguments).replace("'", "''")
    safe_desc = str(description).replace("'", "''")

    ps_script = f"""
$ws = New-Object -ComObject WScript.Shell
$s = $ws.CreateShortcut('{safe_shortcut}')
$s.TargetPath = '{safe_target}'
$s.Arguments = '{safe_args}'
$s.WorkingDirectory = '{safe_work}'
$s.IconLocation = '{safe_icon}'
$s.Description = '{safe_desc}'
$s.Save()
"""
    subprocess.run(["powershell", "-NoProfile", "-Command", ps_script], check=True)


def create_all_shortcuts():
    project_dir = Path(__file__).parent.resolve()
    assets_dir = project_dir / "assets"
    ico_path = assets_dir / "app.ico"

    dist_exe = project_dir / "dist" / "NightLight.exe"

    if dist_exe.exists():
        target = dist_exe
        args = ""
    else:
        python_exe = Path(sys.executable)
        pythonw_exe = python_exe.parent / "pythonw.exe"
        if not pythonw_exe.exists():
            pythonw_exe = python_exe

        target = pythonw_exe
        args = f'"{project_dir / "main.py"}"'

    # 1. Desktop Shortcut
    desktop = Path(os.environ.get("USERPROFILE", "")) / "Desktop"
    if desktop.exists():
        desktop_shortcut = desktop / "Night Light by HT.lnk"
        create_shortcut(
            target_path=target,
            shortcut_path=desktop_shortcut,
            icon_path=ico_path,
            description="Toggle Night Light by HT (left-click) or adjust (right-click)",
            arguments=args,
            working_dir=project_dir,
        )
        print(f"[Shortcuts] Created Desktop shortcut at: {desktop_shortcut}")

    # 2. Start Menu Shortcut (Can be pinned to Taskbar!)
    appdata = Path(os.environ.get("APPDATA", ""))
    start_menu = appdata / "Microsoft" / "Windows" / "Start Menu" / "Programs"
    if start_menu.exists():
        start_shortcut = start_menu / "Night Light by HT.lnk"
        create_shortcut(
            target_path=target,
            shortcut_path=start_shortcut,
            icon_path=ico_path,
            description="Toggle Night Light by HT (left-click) or adjust (right-click)",
            arguments=args,
            working_dir=project_dir,
        )
        print(f"[Shortcuts] Created Start Menu shortcut at: {start_shortcut}")


if __name__ == "__main__":
    create_all_shortcuts()
