import json

import pytest

from config_manager import ConfigManager


@pytest.fixture
def config(tmp_path, monkeypatch):
    monkeypatch.setenv('NIGHT_LIGHT_BY_HT_CONFIG_DIR', str(tmp_path))
    return ConfigManager()


def test_unclosed_session_restores_off_before_restart(config):
    config.transactional_update({'enabled': True, 'smart_enabled': True})
    assert config.begin_session()
    restarted = ConfigManager()
    assert restarted.begin_session()
    assert restarted.recovered_unclean_session
    assert not restarted.get('enabled')
    assert not restarted.get('smart_enabled')
    saved = json.loads(restarted.file_path.read_text())
    assert saved['smart_enabled'] is False


def test_clean_receipt_preserves_saved_mode(config):
    config.begin_session()
    config.transactional_update({'smart_enabled': True})
    config.finish_session()
    restarted = ConfigManager()
    assert restarted.begin_session()
    assert not restarted.recovered_unclean_session
    assert restarted.get('smart_enabled') is True


def test_failed_journal_blocks_automatic_output(config, monkeypatch):
    monkeypatch.setattr(config, '_write_session_record', lambda record: (_ for _ in ()).throw(OSError('disk full')))
    assert config.begin_session() is False
    assert config.automatic_output_blocked


def test_shutdown_save_failure_cannot_issue_clean_receipt(config, monkeypatch):
    config.begin_session()
    monkeypatch.setattr(config, '_save_locked', lambda: (_ for _ in ()).throw(OSError('disk full')))
    with pytest.raises(OSError):
        config.finish_session()
    record=json.loads(config.file_path.with_name('session-recovery.json').read_text())
    assert record['state']=='open'


def test_corrupt_receipt_recovers_off(config):
    config.transactional_update({'smart_enabled': True})
    config._write_session_record({'state': 'bogus'})
    assert config.begin_session()
    assert config.recovered_unclean_session
    assert not config.get('smart_enabled')


def test_unclean_v2_session_recovers_explicit_intent_without_losing_preferences(config):
    preferences={'kind':'personal','evening_ready':'22:00','morning_neutral':'07:00'}
    config.transactional_update({'schema_version':2,'migration_state':'v2',
        'intent_v2':{'mode':'smart','manual':{'warmth_kelvin':4200,'dim_fraction':.1}},
        'smart_settings_v2':preferences,'override_v2':{'kind':'manual_hold'}})
    config.begin_session()
    restarted=ConfigManager()
    assert restarted.begin_session()
    assert restarted.get('intent_v2')['mode']=='off'
    assert restarted.get('intent_v2')['manual']=={'warmth_kelvin':4200,'dim_fraction':.1}
    assert restarted.get('smart_settings_v2')==preferences
    assert restarted.get('override_v2') is None


def test_v2_journal_failure_blocks_intent_in_memory_even_when_disk_cannot_change(config,monkeypatch):
    config.transactional_update({'schema_version':2,'intent_v2':{'mode':'smart'}})
    before=config.file_path.read_bytes()
    monkeypatch.setattr(config,'_write_session_record',lambda record:(_ for _ in ()).throw(OSError('disk full')))
    assert not config.begin_session()
    assert config.get('intent_v2')['mode']=='off' and config.automatic_output_blocked
    assert config.file_path.read_bytes()==before
