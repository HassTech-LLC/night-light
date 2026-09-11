"""Persistence regressions use the isolated directory from conftest only."""
import json

import pytest

from config_manager import ConfigManager


@pytest.fixture
def config(tmp_path, monkeypatch):
    monkeypatch.setenv('NIGHT_LIGHT_BY_HT_CONFIG_DIR', str(tmp_path))
    return ConfigManager()


def test_failed_transaction_preserves_prior_unsaved_edits(config, monkeypatch):
    config.set('appearance', {'accent': '#123456'}, False)
    before = dict(config.data)
    disk = config.file_path.read_bytes()
    monkeypatch.setattr('config_manager.os.replace', lambda *args: (_ for _ in ()).throw(OSError('disk full')))
    with pytest.raises(OSError):
        config.transactional_update({'smart_enabled': True})
    assert config.data == before
    assert config.file_path.read_bytes() == disk
    assert not list(config.file_path.parent.glob('*.tmp'))


def test_transaction_merges_other_writer_and_preserves_ipc(config):
    config.set('ipc_token', 'a' * 40, False)
    config.save_immediate()
    other = ConfigManager()
    other.transactional_update({'theme': 'dark'})
    config.transactional_update({'smart_enabled': True, 'ipc_token': 'b' * 40})
    saved = json.loads(config.file_path.read_text())
    assert saved['theme'] == 'dark'
    assert saved['ipc_token'] == 'a' * 40
    assert saved['smart_enabled'] is True


def test_stale_revision_rejected_without_overwriting(config):
    revision = config.get('config_revision', 0)
    other = ConfigManager()
    other.transactional_update({'theme': 'dark'})
    before = config.file_path.read_bytes()
    with pytest.raises(ValueError, match='changed'):
        config.transactional_update({'smart_enabled': True}, expected_revision=revision)
    assert config.file_path.read_bytes() == before
    assert not config.get('smart_enabled', False)


def test_transaction_rechecks_owner_after_staging_before_replace(config):
    before=config.file_path.read_bytes()
    calls=[]
    def invalidated():
        calls.append('guard')
        raise ValueError('Newer Off invalidated this save')
    with pytest.raises(ValueError,match='Newer Off'):
        config.transactional_update({'smart_enabled':True},before_commit=invalidated)
    assert calls==['guard'] and config.file_path.read_bytes()==before
    assert not config.get('smart_enabled',False)
    assert not list(config.file_path.parent.glob('*.tmp'))
