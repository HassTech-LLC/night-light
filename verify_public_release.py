"""Fail-closed verification for Night Light public-release evidence.

This verifies the structure, candidate binding, hashes, and declared outcomes of
release receipts. It does not manufacture human or hardware evidence and it
does not publish anything.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from datetime import date
from pathlib import Path


TASKS = tuple(f"R{i:03d}" for i in range(1, 31))
PREPUBLICATION_TASKS = TASKS[:27]
REQUIREMENTS = tuple([f"FR-{i:03d}" for i in range(1, 21)] + [f"NFR-{i:03d}" for i in range(1, 7)])
ALLOWED_STATUS = {"NOT_STARTED", "IN_PROGRESS", "PASS", "FAIL", "BLOCKED", "NOT_APPLICABLE_WITH_REASON"}


def digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _mapping(value, name, errors):
    if not isinstance(value, dict):
        errors.append(f"{name} must be an object.")
        return {}
    return value


def _rows(value, name, errors):
    if not isinstance(value, list):
        errors.append(f"{name} must be a list.")
        return []
    return value


def verify_evidence(document: dict, root: Path, phase: str = "candidate") -> list[str]:
    errors: list[str] = []
    if not isinstance(document, dict):
        return ["Evidence document must be an object."]
    if document.get("schema_version") != 1:
        errors.append("Unsupported release evidence schema.")
    candidate = document.get("candidate_id")
    revision = document.get("source_revision")
    installer_hash = document.get("installer_sha256")
    if not isinstance(candidate, str) or not candidate.strip(): errors.append("candidate_id is required.")
    if not isinstance(revision, str) or len(revision) < 7: errors.append("source_revision is required.")
    if not isinstance(installer_hash, str) or len(installer_hash) != 64: errors.append("installer_sha256 is required.")
    if not isinstance(document.get("product_version"), str) or not document["product_version"].strip():
        errors.append("product_version is required.")

    artifacts = _rows(document.get("artifacts"), "artifacts", errors)
    artifact_names = set()
    for row in artifacts:
        if not isinstance(row, dict): errors.append("Artifact row must be an object."); continue
        relative = row.get("path")
        expected = row.get("sha256")
        name = row.get("name")
        if not isinstance(name, str) or name in artifact_names: errors.append("Artifact names must be unique."); continue
        artifact_names.add(name)
        if not isinstance(relative, str) or Path(relative).is_absolute() or ".." in Path(relative).parts:
            errors.append(f"Artifact {name} has an unsafe path."); continue
        path = (root / relative).resolve()
        if root.resolve() not in (path, *path.parents): errors.append(f"Artifact {name} escaped the evidence root."); continue
        if not path.is_file(): errors.append(f"Artifact {name} is missing."); continue
        if not isinstance(expected, str) or digest(path) != expected.lower(): errors.append(f"Artifact {name} hash does not match.")
    installer = next((row for row in artifacts if isinstance(row, dict) and row.get("name") == "installer"), None)
    if not installer or installer.get("sha256") != installer_hash:
        errors.append("Installer artifact is missing or not bound to installer_sha256.")

    tasks = _mapping(document.get("task_results"), "task_results", errors)
    for task in TASKS:
        row = tasks.get(task)
        if not isinstance(row, dict): errors.append(f"{task} has no evidence row."); continue
        status = row.get("status")
        if status not in ALLOWED_STATUS: errors.append(f"{task} has an invalid status.")
        if task in PREPUBLICATION_TASKS and status != "PASS": errors.append(f"{task} is required before approval and is {status}.")
        if status == "PASS" and (not row.get("evidence") or row.get("candidate_id") != candidate):
            errors.append(f"{task} PASS is not evidenced for this candidate.")

    requirements = _mapping(document.get("requirements"), "requirements", errors)
    for requirement in REQUIREMENTS:
        row = requirements.get(requirement)
        if not isinstance(row, dict) or row.get("status") != "PASS":
            errors.append(f"{requirement} is not passed.")
        elif not row.get("evidence") or row.get("candidate_id") != candidate:
            errors.append(f"{requirement} is not evidenced for this candidate.")

    for run in _rows(document.get("test_runs"), "test_runs", errors):
        if not isinstance(run, dict): errors.append("Test run must be an object."); continue
        if run.get("candidate_id") != candidate: errors.append("Test run belongs to another candidate.")
        if any(type(run.get(key)) is not int or run.get(key) < 0 for key in ("tests", "failures", "errors", "required_skipped")):
            errors.append("Test run counts are invalid.")
        elif run["failures"] or run["errors"] or run["required_skipped"]:
            errors.append("A required test run is not green.")
        if not run.get("evidence"): errors.append("Test run has no evidence reference.")
    if not document.get("test_runs"): errors.append("No test runs were supplied.")

    hardware = _rows(document.get("hardware_rows"), "hardware_rows", errors)
    if not hardware: errors.append("No supported hardware rows were supplied.")
    for row in hardware:
        if not isinstance(row, dict) or row.get("status") != "PASS" or row.get("candidate_id") != candidate or not row.get("evidence"):
            errors.append("A supported hardware row is not passed and evidenced for this candidate.")

    usability = _mapping(document.get("usability_result"), "usability_result", errors)
    participants = usability.get("participants")
    rate = usability.get("unassisted_critical_task_rate")
    if type(participants) is not int or not 12 <= participants <= 20: errors.append("Usability requires 12–20 participants.")
    if not isinstance(rate, (int, float)) or isinstance(rate, bool) or not .9 <= rate <= 1: errors.append("Usability task rate is below 90% or invalid.")
    if usability.get("unresolved_serious_defects") != 0 or usability.get("candidate_id") != candidate or not usability.get("evidence"):
        errors.append("Usability result is not clean and evidenced for this candidate.")

    sessions = _rows(document.get("night_sessions"), "night_sessions", errors)
    valid_dates = set()
    for row in sessions:
        if not isinstance(row, dict) or row.get("candidate_id") != candidate or row.get("status") != "PASS" or not row.get("evidence"):
            errors.append("A nightly session is invalid or belongs to another candidate."); continue
        try: session_date = date.fromisoformat(row.get("date", ""))
        except (TypeError, ValueError): errors.append("A nightly session date is invalid."); continue
        if session_date in valid_dates: errors.append("Nightly session dates must be unique.")
        valid_dates.add(session_date)
    if len(valid_dates) < 14: errors.append("Fourteen distinct passing nightly sessions are required.")

    for defect in _rows(document.get("open_defects"), "open_defects", errors):
        if not isinstance(defect, dict): errors.append("Defect row must be an object."); continue
        if defect.get("severity") in {"critical", "high"} and defect.get("status") not in {"closed", "not_reproducible_with_evidence"}:
            errors.append("A critical or high defect remains open.")

    signatures = _rows(document.get("signature_evidence"), "signature_evidence", errors)
    signed_names = {row.get("artifact") for row in signatures if isinstance(row, dict) and row.get("valid") is True and row.get("candidate_id") == candidate and row.get("timestamp_valid") is True}
    if "installer" not in signed_names or "application" not in signed_names:
        errors.append("Application and installer signatures are not both valid for this candidate.")

    staging = _mapping(document.get("staging_receipt"), "staging_receipt", errors)
    if staging.get("candidate_id") != candidate or staging.get("installer_sha256") != installer_hash or staging.get("status") != "PASS" or not staging.get("evidence"):
        errors.append("Staging download-to-install proof is missing or mismatched.")

    if phase in {"promotion", "live"}:
        approval = _mapping(document.get("approval"), "approval", errors)
        if approval.get("status") != "APPROVED_FOR_PROMOTION" or approval.get("candidate_id") != candidate or approval.get("installer_sha256") != installer_hash or not approval.get("approver"):
            errors.append("Exact-artifact promotion approval is missing or mismatched.")
    if phase == "live":
        live = _mapping(document.get("live_receipt"), "live_receipt", errors)
        if live.get("status") != "PASS" or live.get("candidate_id") != candidate or live.get("downloaded_sha256") != installer_hash or live.get("installed_candidate_id") != candidate or not live.get("evidence"):
            errors.append("Live download and installed-runtime proof is missing or mismatched.")
        if tasks.get("R028", {}).get("status") != "PASS" or tasks.get("R029", {}).get("status") != "PASS":
            errors.append("Promotion and live verification tasks are not passed.")
    return errors


def main(argv=None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("evidence", type=Path)
    parser.add_argument("--phase", choices=("candidate", "promotion", "live"), default="candidate")
    args = parser.parse_args(argv)
    root = args.evidence.resolve().parent
    try: document = json.loads(args.evidence.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        print(f"HOLD: evidence could not be read: {exc}")
        return 2
    errors = verify_evidence(document, root, args.phase)
    if errors:
        print("HOLD")
        for error in errors: print(f"- {error}")
        return 2
    state = {"candidate": "READY_FOR_APPROVAL", "promotion": "APPROVED_FOR_PROMOTION", "live": "RELEASE_VERIFIED"}[args.phase]
    print(state)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
