import copy
import hashlib
from pathlib import Path

import pytest

from verify_public_release import REQUIREMENTS, TASKS, verify_evidence


@pytest.fixture
def evidence(tmp_path):
    installer=tmp_path/'NightLightSetup.exe';installer.write_bytes(b'signed installer fixture')
    sha=hashlib.sha256(installer.read_bytes()).hexdigest();candidate='release-1'
    row=lambda evidence:dict(status='PASS',candidate_id=candidate,evidence=evidence)
    document=dict(
        schema_version=1,candidate_id=candidate,product_version='1.0.0',source_revision='a'*40,
        payload_manifest_sha256='b'*64,installer_sha256=sha,
        artifacts=[dict(name='installer',path=installer.name,sha256=sha)],
        signature_evidence=[dict(artifact=name,valid=True,timestamp_valid=True,candidate_id=candidate) for name in ('installer','application')],
        requirements={name:row('requirements.json') for name in REQUIREMENTS},
        task_results={name:row('tasks.json') for name in TASKS},
        test_runs=[dict(candidate_id=candidate,tests=600,failures=0,errors=0,required_skipped=0,evidence='junit.xml')],
        hardware_rows=[dict(status='PASS',candidate_id=candidate,evidence='hardware.json',environment='Windows 11 test VM')],
        usability_result=dict(participants=12,unassisted_critical_task_rate=.92,unresolved_serious_defects=0,candidate_id=candidate,evidence='usability.json'),
        night_sessions=[dict(date=f'2026-09-{day:02d}',status='PASS',candidate_id=candidate,evidence=f'night-{day}.json') for day in range(1,15)],
        open_defects=[],staging_receipt=dict(status='PASS',candidate_id=candidate,installer_sha256=sha,evidence='staging.json'),
        approval=dict(status='APPROVED_FOR_PROMOTION',candidate_id=candidate,installer_sha256=sha,approver='authorized tester'),
        live_receipt=dict(status='PASS',candidate_id=candidate,downloaded_sha256=sha,installed_candidate_id=candidate,evidence='live.json'))
    return tmp_path,document


def test_complete_candidate_and_live_evidence_pass(evidence):
    root,document=evidence
    assert verify_evidence(document,root,'candidate')==[]
    assert verify_evidence(document,root,'promotion')==[]
    assert verify_evidence(document,root,'live')==[]


@pytest.mark.parametrize('mutation,match',[
    (lambda d:d['task_results']['R013'].update(status='BLOCKED'),'R013'),
    (lambda d:d['requirements']['FR-020'].update(status='FAIL'),'FR-020'),
    (lambda d:d['test_runs'][0].update(required_skipped=1),'test run'),
    (lambda d:d['night_sessions'].__setitem__(1,dict(d['night_sessions'][0])),'unique'),
    (lambda d:d['signature_evidence'][0].update(valid=False),'signatures'),
    (lambda d:d['staging_receipt'].update(installer_sha256='0'*64),'Staging'),
])
def test_candidate_gate_fails_closed(evidence,mutation,match):
    root,document=evidence;mutation(document)
    assert any(match.lower() in error.lower() for error in verify_evidence(document,root,'candidate'))


def test_forged_pass_without_evidence_or_wrong_candidate_fails(evidence):
    root,document=evidence
    document['task_results']['R004'].pop('evidence')
    document['requirements']['FR-001']['candidate_id']='other'
    errors=verify_evidence(document,root,'candidate')
    assert any('R004 PASS' in error for error in errors)
    assert any('FR-001' in error and 'candidate' in error for error in errors)


def test_hash_and_live_identity_are_bound(evidence):
    root,document=evidence
    (root/'NightLightSetup.exe').write_bytes(b'modified')
    document['live_receipt']['installed_candidate_id']='other'
    errors=verify_evidence(document,root,'live')
    assert any('hash does not match' in error for error in errors)
    assert any('Live download' in error for error in errors)


def test_promotion_requires_exact_approval(evidence):
    root,document=evidence
    document['approval']['installer_sha256']='f'*64
    assert any('approval' in error.lower() for error in verify_evidence(document,root,'promotion'))
