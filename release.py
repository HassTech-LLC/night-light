"""Create and verify deterministic unsigned Night Light release archives."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import uuid
import zipfile

ROOT = Path(__file__).resolve().parent
ARCHIVE_ROOT = "Night Light"
ZIP_TIME = (1980, 1, 1, 0, 0, 0)
REQUIRED_DIST = (
    "NightLight.exe",
    "wpf_jumplist.exe",
    "shortcut_appid_register.exe",
    "windows_nightlight_off.exe",
    "BINARY-ORIGINS.json",
)
SOURCE_INPUTS = (
    ".github/workflows/ci.yml",
    "NightLight.spec",
    "assets/app.ico",
    "assets/nightlight_active.ico",
    "assets/nightlight_inactive.ico",
    "build.py",
    "build_identity.py",
    "build_installer.py",
    "installer/night-light.nsi",
    "installer/remove-owned.ps1",
    "installer/upgrade.ps1",
    "installer/legacy-installations.json",
    "installer/toolchain.json",
    "installer/README.md",
    "build_premium.py",
    "premium_host.cs",
    "premium_ui.py",
    "premium/settings.html",
    "premium/desktop.js",
    "premium/desktop.css",
    "docs/design/night-light-premium-concept.html",
    "docs/design/appearance.js",
    "docs/design/appearance.css",
    "smart_mode.py",
    "smart_time.py",
    "smart_transition.py",
    "smart_schedule.py",
    "smart_state.py",
    "smart_runtime.py",
    "smart_store.py",
    "smart_desktop.py",
    "smart_migration.py",
    "smart_migration_switch.py",
    "private_config_files.py",
    "smart_learning.py",
    "smart_location.py",
    "smart_windows.py",
    "smart_ui.py",
    "config_manager.py",
    "config_paths.py",
    "create_shortcuts.py",
    "display_status.py",
    "hud_overlay.py",
    "icons.py",
    "ipc_transport.py",
    "LICENSE",
    "NOTICE",
    "main.py",
    "nightlight_engine.py",
    "pyproject.toml",
    "README.md",
    "release.py",
    "shortcut_appid_register.cs",
    "THIRD-PARTY-NOTICES.txt",
    "tray_app.py",
    "uv.lock",
    "win32_tray.py",
    "windows_nightlight.py",
    "windows_nightlight_off.cs",
    "wpf_jumplist.cs",
)


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def _json_bytes(value: object) -> bytes:
    return (json.dumps(value, indent=2, sort_keys=True) + "\n").encode("utf-8")


def source_manifest(project_root: Path) -> dict:
    license_files = sorted((project_root / "THIRD-PARTY-LICENSES").glob("*"))
    inputs = [project_root / name for name in SOURCE_INPUTS] + license_files
    missing = [str(path.relative_to(project_root)) for path in inputs if not path.is_file()]
    if missing:
        raise RuntimeError("missing declared build input(s): " + ", ".join(missing))
    files = [
        {
            "path": path.relative_to(project_root).as_posix(),
            "sha256": sha256_file(path),
            "size": path.stat().st_size,
        }
        for path in sorted(inputs, key=lambda item: item.relative_to(project_root).as_posix())
    ]
    try:
        head = subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=project_root, text=True
        ).strip()
        dirty = bool(
            subprocess.check_output(
                ["git", "status", "--porcelain", "--untracked-files=no"],
                cwd=project_root,
                text=True,
            ).strip()
        )
    except (OSError, subprocess.CalledProcessError):
        head, dirty = None, None
    return {
        "schema_version": 1,
        "product": "Night Light",
        "git_head": head,
        "tracked_worktree_dirty": dirty,
        "files": files,
    }


def project_version() -> str:
    import tomllib
    return tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))["project"]["version"]


def sbom_document(manifest: dict, dist: Path) -> dict:
    app_version = project_version()
    components = [
        ("application", "Night Light", app_version, "GPL-3.0-or-later", None),
        ("framework", "CPython", "3.14.7", "Python-2.0", "pkg:generic/cpython@3.14.7"),
        ("framework", "python-build-standalone", "20260901", "MPL-2.0", "pkg:github/astral-sh/python-build-standalone@20260901"),
        ("library", "OpenSSL", "3.5.8", "Apache-2.0", "pkg:generic/openssl@3.5.8"),
        ("library", "Expat", "2.8.2", "MIT", "pkg:generic/expat@2.8.2"),
        ("library", "XZ/liblzma", "5.8.3", "0BSD", "pkg:generic/xz@5.8.3"),
        ("library", "Tcl/Tk", "9.0.4", "TCL", "pkg:generic/tcl-tk@9.0.4"),
        ("library", "CustomTkinter", "5.2.2", "MIT", "pkg:pypi/customtkinter@5.2.2"),
        ("library", "darkdetect", "0.8.0", "BSD-3-Clause", "pkg:pypi/darkdetect@0.8.0"),
        ("library", "packaging", "26.3", "Apache-2.0 OR BSD-2-Clause", "pkg:pypi/packaging@26.3"),
        ("library", "Pillow", "12.3.0", "HPND", "pkg:pypi/pillow@12.3.0"),
        ("library", "tzdata", "2026.3", "Apache-2.0", "pkg:pypi/tzdata@2026.3"),
        ("library", "tzlocal", "5.4.4", "MIT", "pkg:pypi/tzlocal@5.4.4"),
        ("library", "Roboto", "CustomTkinter-5.2.2", "Apache-2.0", None),
        ("library", "CustomTkinter shapes font", "CustomTkinter-5.2.2", "MIT", None),
        ("library", "zlib-ng (CPython runtime)", "2.2.4", "Zlib", "pkg:generic/zlib-ng@2.2.4"),
        ("library", "Zstandard", "1.5.7", "BSD-3-Clause OR GPL-2.0-only", "pkg:generic/zstd@1.5.7"),
        ("library", "libtommath", "1.3.0", "Unlicense", "pkg:generic/libtommath@1.3.0"),
        ("library", "zlib-ng (Pillow codec)", "2.3.3", "Zlib", "pkg:generic/zlib-ng@2.3.3"),
        ("library", "libjpeg-turbo", "3.1.4.1", "BSD-3-Clause", "pkg:generic/libjpeg-turbo@3.1.4.1"),
        ("library", "libtiff", "4.7.1", "libtiff", "pkg:generic/libtiff@4.7.1"),
        ("library", "FreeType", "2.14.3", "FTL OR GPL-2.0-only", "pkg:generic/freetype@2.14.3"),
        ("library", "Little CMS", "2.19", "MIT", "pkg:generic/littlecms@2.19"),
        ("library", "WebP", "1.6.0", "BSD-3-Clause", "pkg:generic/libwebp@1.6.0"),
        ("library", "libavif", "1.4.2", "BSD-2-Clause", "pkg:generic/libavif@1.4.2"),
        ("library", "OpenJPEG", "2.5.4", "BSD-2-Clause", "pkg:generic/openjpeg@2.5.4"),
        ("library", "SQLite", "3.53.1", "LicenseRef-Public-Domain", "pkg:generic/sqlite@3.53.1"),
        ("library", "bzip2", "1.0.8", "bzip2-1.0.6", "pkg:generic/bzip2@1.0.8"),
        ("library", "libffi", "3.4.8", "MIT", "pkg:generic/libffi@3.4.8"),
        ("library", "mpdecimal", "4.0.0", "BSD-2-Clause", "pkg:generic/mpdecimal@4.0.0"),
        ("library", "Tix", "8.4.3.6", "TCL", "pkg:generic/tix@8.4.3.6"),
        ("application", "PyInstaller bootloader", "6.22.2", "GPL-2.0-or-later WITH Bootloader-exception", "pkg:pypi/pyinstaller@6.22.2"),
    ]
    rows = []
    for kind, name, version, license_id, purl in components:
        if license_id == "LicenseRef-Public-Domain":
            license_choice = {"license": {"name": "Public Domain"}}
        elif " OR " in license_id or " AND " in license_id or " WITH " in license_id:
            license_choice = {"expression": license_id}
        else:
            license_choice = {"license": {"id": license_id}}
        row = {
            "type": kind,
            "name": name,
            "version": version,
            "licenses": [license_choice],
        }
        if purl:
            row["purl"] = purl
        rows.append(row)
    dist_hashes = [
        {"path": path.name, "sha256": sha256_file(path), "size": path.stat().st_size}
        for path in sorted(dist.iterdir())
        if path.is_file()
    ]
    namespace_seed = sha256_bytes(_json_bytes({"manifest": manifest, "dist": dist_hashes}))
    return {
        "bomFormat": "CycloneDX",
        "specVersion": "1.6",
        "serialNumber": f"urn:uuid:{uuid.uuid5(uuid.NAMESPACE_URL, namespace_seed)}",
        "version": 1,
        "metadata": {
            "component": {"type": "application", "name": "Night Light", "version": app_version},
            "properties": [
                {"name": "night-light:unsigned", "value": "true"},
                {"name": "night-light:python-build-source", "value": "python-build-standalone/20260901@4bb01f09aaf362c71e891be4a41cb6d6ddf830b3"},
            ],
        },
        "components": rows,
    }


def _write_zip(path: Path, members: dict[str, bytes]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for name in sorted(members):
            info = zipfile.ZipInfo(name, ZIP_TIME)
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            info.create_system = 3
            archive.writestr(info, members[name], compress_type=zipfile.ZIP_DEFLATED, compresslevel=9)


def validate_build_binding(origins: dict, manifest: dict, sbom: dict, payload_bytes: dict) -> None:
    """Bind packaging claims to recorded build inputs, not the packaging host."""
    recorded = origins.get("source_manifest", {})
    if not recorded.get("files") or recorded.get("files") != manifest.get("files"):
        raise RuntimeError("Build source manifest missing or different; rebuild current source")
    runtime = origins.get("runtime", {})
    python_rows = [row for row in sbom.get("components", []) if row.get("name") == "CPython"]
    if (runtime.get("implementation") != "CPython" or len(python_rows) != 1
            or runtime.get("version") != python_rows[0].get("version")):
        raise RuntimeError("Build runtime does not match release SBOM; qualify the runtime before packaging")
    from build_identity import make_identity
    app_rows=[row for row in sbom.get('components',[]) if row.get('name')=='Night Light' and row.get('type')=='application']
    if len(app_rows)!=1 or origins.get('build_identity')!=make_identity(recorded,app_rows[0]['version'],runtime):
        raise RuntimeError('Embedded build identity record does not match source, runtime and version')
    rows = origins.get("payloads", [])
    for name, data in payload_bytes.items():
        matches = [row for row in rows if row.get("destination") == name]
        if len(matches) != 1 or matches[0].get("sha256") != sha256_bytes(data) or matches[0].get("size") != len(data):
            raise RuntimeError("Build payload binding missing or changed: " + name)


def create_release(dist: Path, output: Path, evidence: Path, *, project_root: Path | None = None) -> dict:
    project_root = (project_root or Path(__file__).resolve().parent).resolve()
    dist, output, evidence = Path(dist).resolve(), Path(output).resolve(), Path(evidence).resolve()
    missing = [name for name in REQUIRED_DIST if not (dist / name).is_file()]
    if missing:
        raise RuntimeError("missing release payload(s): " + ", ".join(missing))
    manifest = source_manifest(project_root)
    sbom = sbom_document(manifest, dist)
    payload_bytes = {name: (dist / name).read_bytes() for name in REQUIRED_DIST}
    validate_build_binding(json.loads(payload_bytes["BINARY-ORIGINS.json"]), manifest, sbom,
                           {name: data for name, data in payload_bytes.items() if name.endswith(".exe")})
    members = {
        f"{ARCHIVE_ROOT}/{name}": data for name, data in payload_bytes.items()
    }
    members[f"{ARCHIVE_ROOT}/LICENSE"] = (project_root / "LICENSE").read_bytes()
    members[f"{ARCHIVE_ROOT}/NOTICE"] = (project_root / "NOTICE").read_bytes()
    members[f"{ARCHIVE_ROOT}/README.md"] = (project_root / "README.md").read_bytes()
    members[f"{ARCHIVE_ROOT}/THIRD-PARTY-NOTICES.txt"] = (project_root / "THIRD-PARTY-NOTICES.txt").read_bytes()
    members[f"{ARCHIVE_ROOT}/SBOM.cdx.json"] = _json_bytes(sbom)
    members[f"{ARCHIVE_ROOT}/SOURCE-MANIFEST.json"] = _json_bytes(manifest)
    for license_path in sorted((project_root / "THIRD-PARTY-LICENSES").iterdir()):
        if license_path.is_file():
            members[f"{ARCHIVE_ROOT}/THIRD-PARTY-LICENSES/{license_path.name}"] = license_path.read_bytes()
    _write_zip(output, members)
    evidence.mkdir(parents=True, exist_ok=True)
    comparison = evidence / ".packaging-reproducibility-check.zip"
    _write_zip(comparison, members)
    packaging_identical = output.read_bytes() == comparison.read_bytes()
    comparison.unlink()
    reproducibility = {
        "schema_version": 1,
        "scope": "archive packaging with identical built payload inputs",
        "byte_identical": packaging_identical,
        "archive_sha256": sha256_file(output),
        "note": "This comparison proves deterministic ZIP assembly, not reproducibility of the PE/compiler outputs.",
    }
    (evidence / "REPRODUCIBILITY.json").write_bytes(_json_bytes(reproducibility))
    (evidence / "sbom.cdx.json").write_bytes(_json_bytes(sbom))
    (evidence / "SOURCE-MANIFEST.json").write_bytes(_json_bytes(manifest))
    sums = {
        output.name: sha256_file(output),
        "sbom.cdx.json": sha256_file(evidence / "sbom.cdx.json"),
        "SOURCE-MANIFEST.json": sha256_file(evidence / "SOURCE-MANIFEST.json"),
        "REPRODUCIBILITY.json": sha256_file(evidence / "REPRODUCIBILITY.json"),
    }
    (evidence / "SHA256SUMS.txt").write_text("".join(f"{digest}  {name}\n" for name, digest in sorted(sums.items())), encoding="utf-8")
    result = verify_release(output, evidence)
    (evidence / "VERIFICATION.json").write_bytes(_json_bytes(result))
    return result


def verify_release(archive_path: Path, evidence: Path | None = None) -> dict:
    archive_path = Path(archive_path).resolve()
    evidence = Path(evidence).resolve() if evidence is not None else None
    errors = []
    required = {f"{ARCHIVE_ROOT}/{name}" for name in REQUIRED_DIST} | {
        f"{ARCHIVE_ROOT}/LICENSE",
        f"{ARCHIVE_ROOT}/NOTICE",
        f"{ARCHIVE_ROOT}/README.md",
        f"{ARCHIVE_ROOT}/THIRD-PARTY-NOTICES.txt",
        f"{ARCHIVE_ROOT}/SBOM.cdx.json",
        f"{ARCHIVE_ROOT}/SOURCE-MANIFEST.json",
        f"{ARCHIVE_ROOT}/THIRD-PARTY-LICENSES/CPython-3.14.7-LICENSE.txt",
    }
    try:
        with zipfile.ZipFile(archive_path) as archive:
            bad = archive.testzip()
            if bad:
                errors.append(f"CRC failure: {bad}")
            missing = sorted(required - set(archive.namelist()))
            if missing:
                errors.append("missing archive members: " + ", ".join(missing))
            sbom = json.loads(archive.read(f"{ARCHIVE_ROOT}/SBOM.cdx.json"))
            origins = json.loads(archive.read(f"{ARCHIVE_ROOT}/BINARY-ORIGINS.json"))
            manifest = json.loads(archive.read(f"{ARCHIVE_ROOT}/SOURCE-MANIFEST.json"))
            validate_build_binding(origins, manifest, sbom, {
                name: archive.read(f"{ARCHIVE_ROOT}/{name}") for name in REQUIRED_DIST if name.endswith(".exe")
            })
            if sbom.get("bomFormat") != "CycloneDX" or sbom.get("specVersion") != "1.6":
                errors.append("invalid CycloneDX SBOM")
            if origins.get("schema_version") != 1 or not isinstance(origins.get("binaries"), list):
                errors.append("invalid binary-origin manifest")
    except (OSError, zipfile.BadZipFile, KeyError, json.JSONDecodeError, RuntimeError) as exc:
        errors.append(str(exc))
    sums_path = evidence / "SHA256SUMS.txt" if evidence is not None else None
    if sums_path is not None and sums_path.is_file():
        expected = {}
        for line in sums_path.read_text(encoding="utf-8").splitlines():
            digest, name = line.split("  ", 1)
            expected[name] = digest
        if expected.get(archive_path.name) != sha256_file(archive_path):
            errors.append("archive SHA-256 mismatch")
    return {
        "schema_version": 1,
        "product": "Night Light",
        "archive": str(archive_path),
        "archive_sha256": sha256_file(archive_path),
        "unsigned": True,
        "valid": not errors,
        "errors": errors,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dist", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--evidence", type=Path)
    parser.add_argument("--verify", type=Path)
    args = parser.parse_args(argv)
    if args.verify:
        result = verify_release(args.verify, args.evidence)
        if args.evidence:
            args.evidence.mkdir(parents=True, exist_ok=True)
            (args.evidence / "VERIFICATION.json").write_bytes(_json_bytes(result))
    else:
        if not args.dist or not args.output or not args.evidence:
            parser.error("--dist, --output, and --evidence are required unless --verify is used")
        result = create_release(args.dist, args.output, args.evidence)
    print(json.dumps(result, indent=2))
    return 0 if result["valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
