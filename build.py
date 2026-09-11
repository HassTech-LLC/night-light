"""
Build Night Light by HT as a standalone Windows executable.

The normal build is side-effect free: it packages files without changing the
current user's Jump List. Pass ``--register-jump-list`` only when deliberately
preparing this Windows account after a successful build.
"""

import argparse
from build_premium import build_premium
import ast
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import shutil
import platform


def _is_within(path: Path, root: Path) -> bool:
    path_key = os.path.normcase(str(path.resolve()))
    root_key = os.path.normcase(str(root.resolve()))
    return path_key == root_key or path_key.startswith(root_key + os.sep)


def validate_binary_origins(entries, *, allowed_roots):
    """Return hashed binary origins or fail on the first undeclared source."""
    roots = [Path(root).resolve() for root in allowed_roots]
    rows = []
    for destination, source, kind in entries:
        origin = Path(source).resolve()
        if not origin.is_file() or not any(_is_within(origin, root) for root in roots):
            raise RuntimeError(
                f"undeclared binary origin for {destination}: {origin}"
            )
        rows.append(
            {
                "destination": destination,
                "origin": str(origin),
                "kind": kind,
                "sha256": hashlib.sha256(origin.read_bytes()).hexdigest(),
                "size": origin.stat().st_size,
            }
        )
    return rows


def _analysis_binary_entries(toc_path: Path):
    analysis = ast.literal_eval(toc_path.read_text(encoding="utf-8"))
    if not isinstance(analysis, tuple) or len(analysis) <= 15:
        raise RuntimeError(f"Unrecognized PyInstaller analysis format: {toc_path}")
    entries = analysis[15]
    if not isinstance(entries, list):
        raise RuntimeError(f"Missing binary inventory in: {toc_path}")
    return entries


def _sanitized_build_environment() -> dict[str, str]:
    env = os.environ.copy()
    windows = Path(os.environ.get("SystemRoot", r"C:\Windows"))
    path_parts = [Path(sys.executable).parent, Path(sys.base_prefix), windows / "System32", windows]
    env["PATH"] = os.pathsep.join(str(path.resolve()) for path in path_parts)
    return env


def _generated_payload(name: str, output: Path, *, sources: list[Path], tool: Path) -> dict:
    return {
        "destination": name,
        "origin": "generated-during-build",
        "sha256": hashlib.sha256(output.read_bytes()).hexdigest(),
        "size": output.stat().st_size,
        "tool": {
            "path": str(tool.resolve()),
            "sha256": hashlib.sha256(tool.read_bytes()).hexdigest(),
        },
        "sources": [
            {
                "path": str(source.resolve()),
                "sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
            }
            for source in sources
        ],
    }


def build(
    register_jump_list: bool = False,
    dist_dir: Path | None = None,
    build_dir: Path | None = None,
) -> Path:
    proj_dir = Path(__file__).parent.resolve()
    assets_dir = proj_dir / "assets"
    ico_path = assets_dir / "app.ico"
    spec_file = proj_dir / "NightLight.spec"
    dist_dir = Path(dist_dir).resolve() if dist_dir else proj_dir / "dist"
    build_dir = Path(build_dir).resolve() if build_dir else proj_dir / "build"
    from release import source_manifest
    source_before = source_manifest(proj_dir)

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
    helper_sources = (cs_file, appid_cs_file, windows_off_cs_file)
    if not all(path.exists() for path in helper_sources):
        missing = ", ".join(str(path.name) for path in helper_sources if not path.exists())
        raise SystemExit(f"Missing native helper source(s): {missing}")
    if not Path(csc_path).exists():
        raise SystemExit(f"Required C# compiler not found: {csc_path}")
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
        "--distpath",
        str(dist_dir),
        "--workpath",
        str(build_dir),
        str(spec_file),
    ]

    build_premium()
    import tomllib
    from build_identity import make_identity
    identity=make_identity(source_before,tomllib.loads((proj_dir/'pyproject.toml').read_text(encoding='utf-8'))['project']['version'],
                           {'implementation':platform.python_implementation(),'version':platform.python_version()})
    (assets_dir/'BUILD-IDENTITY.json').write_text(json.dumps(identity,sort_keys=True,indent=2)+'\n',encoding='utf-8')
    print("Running PyInstaller:", " ".join(cmd))
    res = subprocess.run(cmd, cwd=str(proj_dir), env=_sanitized_build_environment())

    if res.returncode == 0:
        analysis_toc = build_dir / "NightLight" / "Analysis-00.toc"
        allowed_roots = (Path(sys.prefix), Path(sys.base_prefix), proj_dir / 'assets/premium')
        origins = validate_binary_origins(
            _analysis_binary_entries(analysis_toc),
            allowed_roots=allowed_roots,
        )
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
        required_outputs = (exe_path, dist_dir / "wpf_jumplist.exe", dist_dir / "shortcut_appid_register.exe", dist_dir / "windows_nightlight_off.exe")
        missing_outputs = [str(path.name) for path in required_outputs if not path.exists()]
        if missing_outputs:
            raise SystemExit(f"Build incomplete; missing output(s): {', '.join(missing_outputs)}")

        import PyInstaller

        bootloader = Path(PyInstaller.__file__).resolve().parent / "bootloader" / "Windows-64bit-intel" / "runw.exe"
        payloads = [
            _generated_payload(
                "NightLight.exe",
                exe_path,
                sources=[proj_dir / "main.py", spec_file],
                tool=bootloader,
            ),
            _generated_payload("wpf_jumplist.exe", dist_dir / "wpf_jumplist.exe", sources=[cs_file], tool=Path(csc_path)),
            _generated_payload("shortcut_appid_register.exe", dist_dir / "shortcut_appid_register.exe", sources=[appid_cs_file], tool=Path(csc_path)),
            _generated_payload("windows_nightlight_off.exe", dist_dir / "windows_nightlight_off.exe", sources=[windows_off_cs_file], tool=Path(csc_path)),
        ]
        manifest = {
            "schema_version": 1,
            "runtime": {"implementation": platform.python_implementation(), "version": platform.python_version()},
            "build_identity": identity,
            "source_manifest": source_before,
            "policy": "fail-closed",
            "allowed_roots": [str(root.resolve()) for root in allowed_roots],
            "prohibited_origin_markers": ["\\\\jdk", "\\\\java", "\\\\gradle"],
            "binaries": origins,
            "payloads": payloads,
            "embedded_premium": json.loads((proj_dir / 'assets/premium/ORIGINS.json').read_text(encoding='utf-8')),
        }
        origin_text = json.dumps({"binaries": origins, "payloads": payloads})
        if source_manifest(proj_dir)["files"] != source_before["files"]:
            raise RuntimeError("Source changed during build; rebuild before packaging")
        if any(marker.lower() in origin_text.lower() for marker in manifest["prohibited_origin_markers"]):
            raise RuntimeError("prohibited ambient binary origin detected")
        (dist_dir / "BINARY-ORIGINS.json").write_text(
            json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
        )

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
    parser.add_argument("--dist-dir", type=Path, help="Write payloads to this isolated directory.")
    parser.add_argument("--build-dir", type=Path, help="Write PyInstaller intermediates here.")
    args = parser.parse_args()
    build(
        register_jump_list=args.register_jump_list,
        dist_dir=args.dist_dir,
        build_dir=args.build_dir,
    )
