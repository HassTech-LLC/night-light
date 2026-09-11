import json
import pytest
import build_identity


def receipt():
    return build_identity.make_identity({'files':[{'path':'main.py','sha256':'a'*64,'size':1}],
        'git_head':'b'*40,'tracked_worktree_dirty':True},'0.1.0',{'implementation':'CPython','version':'3.14.7'})


def packaged(tmp_path,monkeypatch,value):
    assets=tmp_path/'assets';assets.mkdir()
    (assets/'BUILD-IDENTITY.json').write_text(json.dumps(value),encoding='utf-8')
    monkeypatch.setattr(build_identity.sys,'frozen',True,raising=False)
    monkeypatch.setattr(build_identity.sys,'_MEIPASS',str(tmp_path),raising=False)


def test_source_never_borrows_existing_candidate_receipt(tmp_path,monkeypatch):
    packaged(tmp_path,monkeypatch,receipt())
    monkeypatch.setattr(build_identity.sys,'frozen',False)
    assert build_identity.running_identity()['kind']=='development'


def test_packaged_identity_is_embedded_not_latest_online(tmp_path,monkeypatch):
    value=receipt();packaged(tmp_path,monkeypatch,value)
    result=build_identity.running_identity()
    assert result['kind']=='packaged' and result['version']=='0.1.0'
    assert result['build_id']==value['build_id'] and not result['verified']


@pytest.mark.parametrize('key,value',[('product_id','other-app'),('build_id','stale'),('version','bad'),('channel','stable')])
def test_unknown_or_unqualified_receipts_are_not_shown_as_current(tmp_path,monkeypatch,key,value):
    data=receipt();data[key]=value;packaged(tmp_path,monkeypatch,data)
    assert build_identity.running_identity()['kind']=='unknown'


def test_source_change_changes_build_identity():
    first=receipt()
    second=build_identity.make_identity({'files':[{'path':'main.py','sha256':'c'*64,'size':1}]},'0.1.0',{})
    assert first['build_id']!=second['build_id']


def test_missing_embedded_receipt_does_not_guess(tmp_path,monkeypatch):
    monkeypatch.setattr(build_identity.sys,'frozen',True,raising=False)
    monkeypatch.setattr(build_identity.sys,'_MEIPASS',str(tmp_path),raising=False)
    assert build_identity.running_identity()['kind']=='unknown'
