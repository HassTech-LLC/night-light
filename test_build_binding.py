"""Release claim binding tests; synthetic bytes, no installer or display effects."""
from copy import deepcopy
import pytest
from release import validate_build_binding, sha256_bytes, SOURCE_INPUTS


def test_premium_build_does_not_rewrite_committed_license():
    """Release builds may verify notices but cannot mutate source identity."""
    from pathlib import Path

    source = Path("build_premium.py").read_text(encoding="utf-8")
    assert "copy2(package/'LICENSE.txt'" not in source
    assert "package_license != committed_license" in source


def fixture():
    manifest = {"files": [{"path": "main.py", "sha256": "source", "size": 6}]}
    payload = {"NightLight.exe": b"test-only"}
    origins = {"source_manifest": deepcopy(manifest),
               "runtime": {"implementation": "CPython", "version": "3.14.7"},
               "payloads": [{"destination": name, "sha256": sha256_bytes(data), "size": len(data)}
                            for name, data in payload.items()]}
    sbom = {"components": [{"name": "CPython", "version": "3.14.7"},
                           {"name":"Night Light","type":"application","version":"0.1.0"}]}
    from build_identity import make_identity
    origins['build_identity']=make_identity(manifest,'0.1.0',origins['runtime'])
    return origins, manifest, sbom, payload


def test_matching_binding_is_accepted():
    validate_build_binding(*fixture())


@pytest.mark.parametrize("mutation", ["source", "runtime", "bytes", "missing", "duplicate", "identity"])
def test_stale_or_unproven_build_is_rejected(mutation):
    origins, manifest, sbom, payload = fixture()
    if mutation == "source": manifest["files"][0]["sha256"] = "new-source"
    elif mutation == "runtime": origins["runtime"]["version"] = "3.13.5"
    elif mutation == "bytes": payload["NightLight.exe"] = b"other-version"
    elif mutation == "missing": origins.pop("source_manifest")
    elif mutation == "duplicate": origins["payloads"] *= 2
    elif mutation == "identity": origins['build_identity']['version']='9.9.9'
    with pytest.raises(RuntimeError): validate_build_binding(origins, manifest, sbom, payload)


def test_smart_comfort_sources_are_release_inputs():
    assert set(("smart_time.py", "smart_transition.py", "smart_schedule.py", "smart_state.py",
                "smart_runtime.py", "smart_store.py", "smart_desktop.py", "smart_migration.py",
                "private_config_files.py")) <= set(SOURCE_INPUTS)
