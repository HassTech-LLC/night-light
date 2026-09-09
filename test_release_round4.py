from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parent


def test_tray_icon_dispatches_clicks_and_updates_running_backend():
    from win32_tray import WM_CONTEXTMENU, WM_LBUTTONUP, WM_RBUTTONUP, TrayIcon

    events = []

    class FakeBackend:
        def __init__(self, owner):
            self.owner = owner
            self.updates = []
            self.ran = False
            self.stopped = False

        def run(self):
            self.ran = True

        def update(self):
            self.updates.append((self.owner.icon, self.owner.title))

        def stop(self):
            self.stopped = True

    icon = TrayIcon(
        name="NightLight",
        icon="inactive",
        title="Night Light off",
        on_left_click=lambda tray: events.append(("left", tray.name)),
        on_right_click=lambda tray: events.append(("right", tray.name)),
        backend_factory=FakeBackend,
    )
    icon.run_detached()
    icon._handle_message(WM_LBUTTONUP)
    icon._handle_message(WM_RBUTTONUP)
    icon._handle_message(WM_CONTEXTMENU)
    icon.icon = "active"
    icon.title = "Night Light on"
    icon.stop()

    assert events == [("left", "NightLight"), ("right", "NightLight"), ("right", "NightLight")]
    assert icon._backend.ran is True
    assert icon._backend.updates == [("active", "Night Light off"), ("active", "Night Light on")]
    assert icon._backend.stopped is True


def test_win32_tray_configures_pointer_sized_api_results():
    import ctypes
    from ctypes import wintypes

    from win32_tray import _configure_win32_api

    class Function:
        def __call__(self, *args):
            return 1

    class API:
        pass

    user32 = API()
    for name in ("RegisterClassW", "CreateWindowExW", "LoadImageW", "DestroyIcon", "PostMessageW", "GetMessageW", "TranslateMessage", "DispatchMessageW", "DestroyWindow", "PostQuitMessage", "DefWindowProcW"):
        setattr(user32, name, Function())
    shell32 = API()
    shell32.Shell_NotifyIconW = Function()
    kernel32 = API()
    kernel32.GetModuleHandleW = Function()

    _configure_win32_api(user32, shell32, kernel32)

    assert user32.CreateWindowExW.restype is wintypes.HWND
    assert user32.LoadImageW.restype is wintypes.HANDLE
    assert kernel32.GetModuleHandleW.restype is wintypes.HMODULE
    assert user32.DefWindowProcW.restype is ctypes.c_ssize_t


def test_build_accepts_isolated_output_directories():
    import inspect
    from build import build

    parameters = inspect.signature(build).parameters
    assert "dist_dir" in parameters
    assert "build_dir" in parameters


def test_binary_origin_allowlist_fails_closed(tmp_path):
    from build import validate_binary_origins

    runtime = tmp_path / "python"
    runtime.mkdir()
    allowed = runtime / "python314.dll"
    allowed.write_bytes(b"runtime")
    outside = tmp_path / "jdk-21" / "bin" / "ucrtbase.dll"
    outside.parent.mkdir(parents=True)
    outside.write_bytes(b"ambient")

    rows = validate_binary_origins(
        [("python314.dll", str(allowed), "BINARY")],
        allowed_roots=[runtime],
    )
    assert rows[0]["origin"] == str(allowed.resolve())

    with pytest.raises(RuntimeError, match="undeclared binary origin"):
        validate_binary_origins(
            [("ucrtbase.dll", str(outside), "BINARY")],
            allowed_roots=[runtime],
        )


def test_ci_uses_immutable_actions_and_exact_tool_versions():
    import re

    workflow = (ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
    action_refs = re.findall(r"^\s*uses:\s*[^@\s]+@([^\s#]+)", workflow, flags=re.MULTILINE)
    assert action_refs
    assert all(re.fullmatch(r"[0-9a-f]{40}", ref) for ref in action_refs)
    assert 'NIGHT_LIGHT_PYTHON: "3.14.7"' in workflow
    assert 'NIGHT_LIGHT_PYTHON_BUILD: "20260901"' in workflow
    assert "UV_PYTHON_PREFERENCE: only-managed" in workflow
    assert "uv python install $env:NIGHT_LIGHT_PYTHON --managed-python --no-bin --no-registry" in workflow
    assert 'version: "0.12.9"' in workflow
    assert "WINDOWS_SIGNING_CERTIFICATE_BASE64" in workflow
    assert "WINDOWS_SIGNING_CERTIFICATE_PASSWORD" in workflow
    assert "attest-build-provenance" in workflow


def test_release_bundle_is_deterministic_and_self_verifying(tmp_path):
    import hashlib
    import json
    import zipfile

    from release import create_release, verify_release

    dist = tmp_path / "dist"
    dist.mkdir()
    for name, payload in {
        "NightLight.exe": b"night-light",
        "wpf_jumplist.exe": b"jump-list",
        "shortcut_appid_register.exe": b"appid",
        "windows_nightlight_off.exe": b"night-light-off",
        "BINARY-ORIGINS.json": b'{"schema_version":1,"binaries":[]}\n',
    }.items():
        (dist / name).write_bytes(payload)

    first = tmp_path / "first.zip"
    second = tmp_path / "second.zip"
    evidence = tmp_path / "evidence"
    create_release(dist, first, evidence, project_root=ROOT)
    create_release(dist, second, tmp_path / "evidence-2", project_root=ROOT)

    assert first.read_bytes() == second.read_bytes()
    receipt = verify_release(first, evidence)
    assert receipt["valid"] is True
    with zipfile.ZipFile(first) as archive:
        names = set(archive.namelist())
        assert "Night Light/THIRD-PARTY-NOTICES.txt" in names
        assert "Night Light/THIRD-PARTY-LICENSES/CPython-3.14.7-LICENSE.txt" in names
        assert "Night Light/SBOM.cdx.json" in names
        assert "Night Light/BINARY-ORIGINS.json" in names
        sbom = json.loads(archive.read("Night Light/SBOM.cdx.json"))
        assert sbom["bomFormat"] == "CycloneDX"
        assert any(component["name"] == "CPython" and component["version"] == "3.14.7" for component in sbom["components"])
        for component in sbom["components"]:
            choice = component["licenses"][0]
            assert ("expression" in choice) or (" " not in choice["license"].get("id", ""))
        sqlite = next(component for component in sbom["components"] if component["name"] == "SQLite")
        assert sqlite["licenses"][0]["license"]["name"] == "Public Domain"
    from release import main
    assert main(["--verify", str(first)]) == 0
    expected = hashlib.sha256(first.read_bytes()).hexdigest()
    assert expected in (evidence / "SHA256SUMS.txt").read_text(encoding="utf-8")


def test_release_sources_do_not_reference_pystray_or_six_runtime_dependency():
    scanned = [ROOT / "tray_app.py", ROOT / "NightLight.spec", ROOT / "pyproject.toml", ROOT / "uv.lock"]
    joined = "\n".join(path.read_text(encoding="utf-8").lower() for path in scanned)
    assert "pystray" not in joined
    assert 'name = "six"' not in (ROOT / "uv.lock").read_text(encoding="utf-8").lower()
