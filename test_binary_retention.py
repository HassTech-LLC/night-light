import hashlib
import pytest


def test_streamed_backup_verifies_expected_bytes_and_private_access(tmp_path):
    from private_config_files import retain_private_binary,access_descriptor
    acl=tmp_path/'config.json';acl.write_bytes(b'{}')
    source=tmp_path/'old.exe';source.write_bytes(b'fixture'*300000)
    expected=hashlib.sha256(source.read_bytes()).hexdigest()
    target=tmp_path/'old.payload'
    retain_private_binary(acl,source,target,expected)
    assert target.read_bytes()==source.read_bytes()
    assert access_descriptor(target)==access_descriptor(acl)
    retain_private_binary(acl,source,target,expected)  # Verified reuse.


def test_source_changed_after_hash_cannot_publish_backup(tmp_path):
    from private_config_files import retain_private_binary
    acl=tmp_path/'config.json';acl.write_bytes(b'{}')
    source=tmp_path/'old.exe';source.write_bytes(b'changed')
    target=tmp_path/'old.payload'
    with pytest.raises(OSError,match='changed'):
        retain_private_binary(acl,source,target,hashlib.sha256(b'original').hexdigest())
    assert not target.exists() and not list(tmp_path.glob('.private-binary-*'))


def test_existing_corrupt_binary_is_not_overwritten(tmp_path):
    from private_config_files import retain_private_binary
    acl=tmp_path/'config.json';acl.write_bytes(b'{}')
    source=tmp_path/'old.exe';source.write_bytes(b'original')
    target=tmp_path/'old.payload';target.write_bytes(b'corrupt')
    with pytest.raises(OSError,match='match'):
        retain_private_binary(acl,source,target,hashlib.sha256(b'original').hexdigest())
    assert target.read_bytes()==b'corrupt'


def test_access_failure_publishes_no_binary_bytes(tmp_path,monkeypatch):
    import private_config_files as files
    acl=tmp_path/'config.json';acl.write_bytes(b'{}')
    source=tmp_path/'old.exe';source.write_bytes(b'original')
    target=tmp_path/'old.payload'
    monkeypatch.setattr(files,'copy_file_access',lambda *a:(_ for _ in ()).throw(OSError('ACL failure')))
    with pytest.raises(OSError,match='ACL'):
        files.retain_private_binary(acl,source,target,hashlib.sha256(b'original').hexdigest())
    assert not target.exists() and not list(tmp_path.glob('.private-binary-*'))
