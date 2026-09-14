"""Keep the project's GPL license consistent across release surfaces."""

from pathlib import Path
import tomllib

import release


ROOT = Path(__file__).resolve().parent
LICENSE_ID = "GPL-3.0-or-later"
GPL_FIRST_LINE = "                    GNU GENERAL PUBLIC LICENSE"


def test_root_license_is_verbatim_gpl3():
    license_text = (ROOT / "LICENSE").read_text(encoding="utf-8")
    assert license_text.splitlines()[0] == GPL_FIRST_LINE
    assert "Version 3, 29 June 2007" in license_text
    # The GPL text is never edited; additional permissions belong in NOTICE.
    assert "WebView2" not in license_text


def test_notice_carries_copyright_and_the_webview2_exception():
    notice = (ROOT / "NOTICE").read_text(encoding="utf-8")
    assert "Copyright (C) 2026 HassTech" in notice
    assert "GNU General Public License" in notice
    assert "ADDITIONAL PERMISSION UNDER GNU GPL VERSION 3 SECTION 7" in notice
    assert "Microsoft Edge WebView2" in notice


def test_project_metadata_declares_the_gpl():
    metadata = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))["project"]
    assert metadata["license"] == LICENSE_ID
    assert metadata["license-files"] == ["LICENSE", "NOTICE"]
    # PEP 639: the SPDX expression is authoritative, so no License:: classifier.
    assert not any(value.startswith("License ::") for value in metadata["classifiers"])


def test_release_manifest_and_sbom_use_the_gpl(tmp_path):
    assert "NOTICE" in release.SOURCE_INPUTS
    dist = tmp_path / "dist"
    dist.mkdir()
    sbom = release.sbom_document({"files": []}, dist)
    app = next(component for component in sbom["components"] if component["name"] == "Night Light")
    assert app["licenses"] == [{"license": {"id": LICENSE_ID}}]


def test_no_release_surface_still_advertises_the_noncommercial_license():
    for name in ("NOTICE", "THIRD-PARTY-NOTICES.txt", "pyproject.toml", "release.py"):
        text = (ROOT / name).read_text(encoding="utf-8")
        assert "PolyForm" not in text, name
    # The README may describe the change in history, but never as the current grant.
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    assert "PolyForm-Noncommercial-1.0.0" not in readme
