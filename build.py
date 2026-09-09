"""
Build Night Light by HT as a standalone Windows executable.

The normal build is side-effect free: it packages files without changing the
current user's Jump List. Pass ``--register-jump-list`` only when deliberately
preparing this Windows account after a successful build.
"""

import argparse
from pathlib import Path
import subprocess
import sys
import shutil


def build(register_jump_list: bool = False) -> Path:
    proj_dir = Path(__file__).parent.resolve()
    assets_dir = proj_dir / "assets"
    ico_path = assets_dir / "app.ico"
    spec_file = proj_dir / "NightLight.spec"
    dist_dir = proj_dir / "dist"
    build_dir = proj_dir / "build"

    # Ensure icon exists
    if not ico_path.exists():
        import icons
        icons.save_ico(str(ico_path))

    # Compile wpf_jumplist.exe
    cs_file = proj_dir / "wpf_jumplist.cs"
    jl_exe = proj_dir / "wpf_jumplist.exe"
    appid_cs_file = proj_dir / "shortcut_appid_register.cs"
    appid_exe = proj_dir / "shortcut_appid_register.exe"
    windows_off_cs_file = proj_dir / "windows_nightlight_off.cs"
    windows_off_exe = proj_dir / "windows_nightlight_off.exe"
    csc_path = r"C:\Windows\Microsoft.NET\Framework64\v4.0.30319\csc.exe"
    if cs_file.exists() and Path(csc_path).exists():
        print("Compiling wpf_jumplist.exe...")
        subprocess.run([
            csc_path, "/nologo",
            r'/r:C:\Windows\Microsoft.NET\Framework64\v4.0.30319\WPF\PresentationFramework.dll',
            r'/r:C:\Windows\Microsoft.NET\Framework64\v4.0.30319\WPF\WindowsBase.dll',
            r'/r:C:\Windows\Microsoft.NET\Framework64\v4.0.30319\WPF\PresentationCore.dll',
            r'/r:C:\Windows\Microsoft.NET\Framework64\v4.0.30319\System.Xaml.dll',
            f"/out:{jl_exe}", str(cs_file)
        ], check=True)

    if appid_cs_file.exists() and Path(csc_path).exists():
        print("Compiling shortcut_appid_register.exe...")
        subprocess.run([
            csc_path, "/nologo", f"/out:{appid_exe}", str(appid_cs_file)
        ], check=True)

    if windows_off_cs_file.exists() and Path(csc_path).exists():
        print("Compiling windows_nightlight_off.exe...")
        subprocess.run([
            csc_path, "/nologo",
            r'/r:C:\Windows\Microsoft.NET\assembly\GAC_MSIL\UIAutomationClient\v4.0_4.0.0.0__31bf3856ad364e35\UIAutomationClient.dll',
            r'/r:C:\Windows\Microsoft.NET\assembly\GAC_MSIL\UIAutomationTypes\v4.0_4.0.0.0__31bf3856ad364e35\UIAutomationTypes.dll',
            f"/out:{windows_off_exe}", str(windows_off_cs_file)
        ], check=True)

    cmd = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--clean",
        "--noconfirm",
        str(spec_file),
    ]

    print("Running PyInstaller:", " ".join(cmd))
    res = subprocess.run(cmd, cwd=str(proj_dir))

    if res.returncode == 0:
        exe_path = dist_dir / "NightLight.exe"
        if jl_exe.exists():
            shutil.copy(jl_exe, dist_dir / "wpf_jumplist.exe")
            if register_jump_list:
                subprocess.run(
                    [str(dist_dir / "wpf_jumplist.exe"), str(exe_path)],
                    check=True,
                )
        if appid_exe.exists():
            shutil.copy(appid_exe, dist_dir / "shortcut_appid_register.exe")
        if windows_off_exe.exists():
            shutil.copy(windows_off_exe, dist_dir / "windows_nightlight_off.exe")

        print("\n Build successful! Standalone executable created at:")
        print(f"-> {exe_path}\n")
        return exe_path

    raise SystemExit(f"PyInstaller failed with return code {res.returncode}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--register-jump-list",
        action="store_true",
        help="Register the generated Jump List on this Windows account.",
    )
    args = parser.parse_args()
    build(register_jump_list=args.register_jump_list)
