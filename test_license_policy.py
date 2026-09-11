"""Keep the project's noncommercial license consistent across release surfaces."""

from pathlib import Path
import tomllib

import release


ROOT = Path(__file__).resolve().parent
LICENSE_NAME = "PolyForm Noncommercial License 1.0.0"
LICENSE_ID = "PolyForm-Noncommercial-1.0.0"


def test_root_license_and_required_notice_are_present():
    license_text = (ROOT / "LICENSE").read_text(encoding="utf-8")
    notice_text = (ROOT / "NOTICE").read_text(encoding="utf-8")
    assert license_text.startswith(f"# {LICENSE_NAME}\n")
    assert notice_text == "Required Notice: Copyright 2026 HassTech\n"


def test_project_metadata_does_not_claim_mit_or_osi_approval():
    metadata = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))["project"]
    assert metadata["license"] == LICENSE_ID
    assert metadata["license-files"] == ["LICENSE", "NOTICE"]
    assert "License :: OSI Approved :: MIT License" not in metadata["classifiers"]


def test_release_manifest_and_sbom_use_noncommercial_license(tmp_path):
    assert "NOTICE" in release.SOURCE_INPUTS
    dist = tmp_path / "dist"
    dist.mkdir()
    sbom = release.sbom_document({"files": []}, dist)
    app = next(component for component in sbom["components"] if component["name"] == "Night Light")
    assert app["licenses"] == [{"license": {"id": LICENSE_ID}}]
