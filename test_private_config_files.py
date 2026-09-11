import json
import pytest
from private_config_files import copy_file_access, access_descriptor, write_private_backup


def test_empty_copy_preserves_access(tmp_path):
    source=tmp_path/'source.json';target=tmp_path/'empty.json'
    source.touch();target.touch()
    try:copy_file_access(source,target)
    except OSError:
        assert access_descriptor(source)==access_descriptor(target)
        raise


def test_private_backup_matches_bytes_and_owner_group_dacl(tmp_path):
    source=tmp_path/'config.json';source.write_bytes(b'{"fixture":"not user data"}')
    target=tmp_path/'config.pre-v2-fixture.json'
    write_private_backup(source,target,source.read_bytes())
    assert source.read_bytes()==target.read_bytes()
    assert access_descriptor(source)==access_descriptor(target)
    with pytest.raises(FileExistsError):write_private_backup(source,target,b'different')
    assert target.read_bytes()==source.read_bytes()


def test_access_failure_leaves_no_plaintext_backup(tmp_path,monkeypatch):
    source=tmp_path/'config.json';source.write_bytes(b'private fixture')
    target=tmp_path/'config.pre-v2-fixture.json'
    monkeypatch.setattr('private_config_files.copy_file_access',lambda *a:(_ for _ in ()).throw(OSError('ACL unavailable')))
    with pytest.raises(OSError,match='ACL'):write_private_backup(source,target,source.read_bytes())
    assert not target.exists() and list(tmp_path.iterdir())==[source]


def test_backup_rejects_other_directories(tmp_path):
    source=tmp_path/'config.json';source.write_bytes(b'fixture')
    other=tmp_path/'other';other.mkdir()
    with pytest.raises(ValueError,match='same directory'):
        write_private_backup(source,other/'backup.json',b'fixture')


def test_regular_config_save_retains_access_descriptor(tmp_path,monkeypatch):
    from config_manager import ConfigManager
    monkeypatch.setenv('NIGHT_LIGHT_BY_HT_CONFIG_DIR',str(tmp_path))
    config=ConfigManager()
    before=access_descriptor(config.file_path)
    config.transactional_update({'fixture':'value'})
    assert access_descriptor(config.file_path)==before


def test_protected_dacl_stays_protected_on_backup_and_save(tmp_path,monkeypatch):
    from config_manager import ConfigManager
    from private_config_files import _api,_access
    monkeypatch.setenv('NIGHT_LIGHT_BY_HT_CONFIG_DIR',str(tmp_path))
    config=ConfigManager()
    adv,_=_api()
    with _access(config.file_path) as (_,_,dacl,_,_):
        assert adv.SetNamedSecurityInfoW(str(config.file_path),1,4|0x80000000,None,None,dacl,None)==0
    before=access_descriptor(config.file_path)
    assert 'D:P' in before
    target=tmp_path/'config.pre-v2-protected.json'
    write_private_backup(config.file_path,target,config.file_path.read_bytes())
    assert access_descriptor(target)==before
    config.transactional_update({'fixture':'protected'})
    assert access_descriptor(config.file_path)==before
