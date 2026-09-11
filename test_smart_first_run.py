import pytest
from config_manager import ConfigManager


def test_fresh_configuration_gets_neutral_v2_without_autostart(tmp_path,monkeypatch):
    from smart_migration import initialize_first_install
    monkeypatch.setenv('NIGHT_LIGHT_BY_HT_CONFIG_DIR',str(tmp_path))
    config=ConfigManager()
    assert initialize_first_install(config)
    assert config.get('migration_state')=='v2'
    assert config.get('intent_v2')['mode']=='off'
    assert not config.get('autostart') and not config.get('smart_learning')
    assert config.get('onboarding_v2')['completed'] is False
    assert not initialize_first_install(config)


def test_existing_off_install_is_not_mistaken_for_first_run(tmp_path,monkeypatch):
    from smart_migration import initialize_first_install
    monkeypatch.setenv('NIGHT_LIGHT_BY_HT_CONFIG_DIR',str(tmp_path))
    config=ConfigManager();config.save_immediate()
    existing=ConfigManager();original=existing.file_path.read_bytes()
    assert not initialize_first_install(existing)
    assert existing.file_path.read_bytes()==original


def test_first_run_never_overwrites_other_process_settings(tmp_path,monkeypatch):
    from smart_migration import initialize_first_install
    monkeypatch.setenv('NIGHT_LIGHT_BY_HT_CONFIG_DIR',str(tmp_path))
    config=ConfigManager()
    other=ConfigManager();other.transactional_update({'temperature_k':3000,'enabled':True})
    original=other.file_path.read_bytes()
    with pytest.raises(ValueError,match='changed'):initialize_first_install(config)
    assert other.file_path.read_bytes()==original


def test_modified_new_config_requires_review_instead_of_defaults(tmp_path,monkeypatch):
    from smart_migration import initialize_first_install
    monkeypatch.setenv('NIGHT_LIGHT_BY_HT_CONFIG_DIR',str(tmp_path))
    config=ConfigManager();config.transactional_update({'smart_location':{'latitude':42.,'longitude':-83.}})
    original=config.file_path.read_bytes()
    assert not initialize_first_install(config)
    assert config.file_path.read_bytes()==original
