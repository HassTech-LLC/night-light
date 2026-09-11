import json
from dataclasses import replace
from pathlib import Path
import pytest
from smart_migration import inspect_legacy, propose_migration, migration_patch, new_install_patch
from smart_state import SmartSettings,Appearance


def fixture(name):
    return json.loads((Path(__file__).parent/'tests'/'fixtures'/'smart_config'/f'{name}.json').read_text())


def test_migration_inventory_is_allowlisted_and_does_not_expose_history_or_secrets():
    source=fixture('legacy-learning')
    inventory=inspect_legacy(source)
    encoded=json.dumps(inventory)
    assert inventory['mode']=='smart' and inventory['legacy_collection_enabled']
    assert inventory['location']['latitude']==42.3353
    assert 'ipc_token' not in encoded and 'REDACTED' not in encoded and 'smart_nights' not in encoded
    assert source==fixture('legacy-learning')


def test_proposal_and_keep_do_not_mutate_current_schedule():
    source=fixture('legacy-learning')
    proposal=propose_migration(source,SmartSettings(kind='solar',latitude=42.3353,longitude=-83.2864))
    assert migration_patch(source,proposal,choice='keep')=={}
    assert source==fixture('legacy-learning')


def test_switch_preserves_off_preferences_unknown_fields_and_consent_history():
    source=fixture('legacy-off')
    proposal=propose_migration(source,SmartSettings(kind='personal',evening_ready='22:00',morning_neutral='07:15'))
    patch=migration_patch(source,proposal,choice='switch',previewed=True)
    result=dict(source,**patch)
    assert result['schema_version']==2 and result['migration_state']=='v2'
    assert result['intent_v2']['mode']=='off'
    assert result['intent_v2']['manual']['warmth_kelvin']==3500
    assert result['theme']==source['theme'] and result['autostart']==source['autostart']
    assert result['ipc_token']==source['ipc_token']
    assert 'ipc_token' not in result['legacy_v1']
    assert result['legacy_v1']['smart_quiet_hours']==source['smart_quiet_hours']


def test_switch_requires_preview_and_rejects_source_changes():
    source=fixture('legacy-learning')
    proposal=propose_migration(source,SmartSettings(kind='personal'))
    with pytest.raises(ValueError,match='preview'):migration_patch(source,proposal,choice='switch')
    changed=dict(source,theme='changed')
    with pytest.raises(ValueError,match='changed'):
        migration_patch(changed,proposal,choice='switch',previewed=True)


def test_switch_stops_collection_but_does_not_delete_history():
    source=fixture('legacy-learning')
    proposal=propose_migration(source,SmartSettings(kind='personal'))
    result=dict(source,**migration_patch(source,proposal,choice='switch',previewed=True))
    assert result['smart_learning'] is False
    assert result['smart_nights']==source['smart_nights']
    assert result['legacy_v1']['smart_learning'] is True
    assert result['future_extension']==source['future_extension']
    assert result['enabled'] is False and result['smart_enabled'] is False


def test_invalid_legacy_appearance_requires_an_explicit_replacement_not_clamping():
    source=fixture('legacy-out-of-range')
    info=inspect_legacy(source)
    assert info['manual'] is None and info['location'] is None
    proposal=propose_migration(source,SmartSettings(kind='personal'))
    with pytest.raises(ValueError,match='appearance'):
        migration_patch(source,proposal,choice='switch',previewed=True)
    proposal=propose_migration(source,SmartSettings(kind='personal'),manual=Appearance(4000,0))
    patch=migration_patch(source,proposal,choice='switch',previewed=True)
    assert patch['intent_v2']['manual']=={'warmth_kelvin':4000,'dim_fraction':0}
    assert patch['legacy_v1']['temperature_k']==1000


def test_new_install_starts_off_without_collection_or_autostart():
    result=new_install_patch()
    assert result['intent_v2']['mode']=='off' and result['migration_state']=='v2'
    assert result['smart_learning'] is False and result['autostart'] is False
    assert result['onboarding_v2']['completed'] is False


def test_migration_does_not_trust_learning_as_new_timing_authority():
    source=fixture('legacy-learning')
    proposal=propose_migration(source,SmartSettings(kind='personal',evening_ready='21:45',morning_neutral='06:30'))
    patch=migration_patch(source,proposal,choice='switch',previewed=True)
    assert patch['smart_settings_v2']['evening_ready']=='21:45'
    assert patch['smart_settings_v2']['morning_neutral']=='06:30'


def test_v2_blocks_legacy_collector_even_if_old_collection_flag_is_true():
    from datetime import datetime,timedelta,timezone
    from smart_learning import TimingLearner
    data={'schema_version':2,'migration_state':'v2','smart_learning':True,'smart_nights':[]}
    class Config(dict):
        def set(self,*args,**kwargs):pytest.fail('V2 must not write routine observations')
    learner=TimingLearner(Config(data))
    now=datetime(2026,9,9,23,tzinfo=timezone.utc)
    learner.observe(now,3600)
    learner.observe(now+timedelta(hours=8),0)
    learner.record(now,now+timedelta(hours=8))
    assert learner.last_active is None and learner.pending is None


def test_v2_cannot_accidentally_run_legacy_scheduler():
    from smart_mode import SmartController
    class Engine:
        def set_state(self,**kwargs):pytest.fail('Legacy scheduler must not own v2 output')
    config={'schema_version':2,'migration_state':'v2','smart_enabled':True,'smart_learning':True}
    controller=SmartController(Engine(),config)
    controller.tick()
    assert not controller.enabled and 'legacy scheduler stopped' in controller.status


def test_legacy_pending_retains_existing_consented_learning_behavior():
    from datetime import datetime,timedelta,timezone
    from smart_learning import TimingLearner
    class Config(dict):
        def set(self,key,value):self[key]=value
    config=Config(schema_version=2,migration_state='legacy_pending',smart_learning=True)
    learner=TimingLearner(config)
    now=datetime(2026,9,9,23,tzinfo=timezone.utc)
    learner.record(now,now+timedelta(hours=8))
    assert len(config['smart_nights'])==1


def test_only_a_missing_file_is_classified_as_a_fresh_install(tmp_path,monkeypatch):
    from config_manager import ConfigManager
    monkeypatch.setenv('NIGHT_LIGHT_BY_HT_CONFIG_DIR',str(tmp_path))
    first=ConfigManager()
    assert first.created_new
    second=ConfigManager()
    assert not second.created_new and not second.get('enabled')


def test_fresh_file_creation_keeps_the_initial_writer_lock(tmp_path,monkeypatch):
    import config_manager
    from contextlib import contextmanager
    monkeypatch.setenv('NIGHT_LIGHT_BY_HT_CONFIG_DIR',str(tmp_path))
    original=config_manager.config_file_lock
    acquisitions=[]
    @contextmanager
    def tracked(path):
        acquisitions.append(path)
        with original(path):yield
    monkeypatch.setattr(config_manager,'config_file_lock',tracked)
    config=config_manager.ConfigManager()
    assert config.created_new and len(acquisitions)==1


def test_two_simultaneous_starters_have_only_one_fresh_creator(tmp_path,monkeypatch):
    from config_manager import ConfigManager
    from concurrent.futures import ThreadPoolExecutor
    from threading import Barrier
    monkeypatch.setenv('NIGHT_LIGHT_BY_HT_CONFIG_DIR',str(tmp_path))
    start=Barrier(2)
    def create():
        start.wait(timeout=5)
        return ConfigManager().created_new
    with ThreadPoolExecutor(max_workers=2) as pool:
        futures=[pool.submit(create) for _ in range(2)]
        assert sorted(f.result(timeout=5) for f in futures)==[False,True]


def test_migration_persists_verified_private_backup_before_switch(tmp_path,monkeypatch):
    from config_manager import ConfigManager
    from smart_migration import commit_migration
    from private_config_files import access_descriptor
    monkeypatch.setenv('NIGHT_LIGHT_BY_HT_CONFIG_DIR',str(tmp_path))
    config=ConfigManager()
    config.transactional_update(fixture('legacy-learning'))
    proposal=propose_migration(config.data,SmartSettings(kind='personal'))
    before=config.file_path.read_bytes()
    binary=tmp_path/'fixture-old.exe';binary.write_bytes(b'fixture binary, never executed')
    receipt=commit_migration(config,proposal,previewed=True,binary_path=binary)
    backup=tmp_path/receipt['config_backup']
    assert backup.read_bytes()==before
    assert access_descriptor(backup)==access_descriptor(config.file_path)
    assert config.get('migration_state')=='v2' and not config.get('smart_learning')
    assert receipt['binary_retained'] is True
    retained=tmp_path/receipt['binary_backup']
    assert retained.read_bytes()==binary.read_bytes()
    assert access_descriptor(retained)==access_descriptor(config.file_path)
    assert retained.suffix=='.payload'  # No competing launchable app shortcut.
    assert 'REDACTED' not in json.dumps(receipt)


@pytest.mark.parametrize('damage',[None,'binary','config','path'])
def test_retained_pair_verification_checks_content_and_confines_paths(tmp_path,monkeypatch,damage):
    from config_manager import ConfigManager
    from smart_migration import commit_migration,verify_retained_migration_files
    monkeypatch.setenv('NIGHT_LIGHT_BY_HT_CONFIG_DIR',str(tmp_path))
    config=ConfigManager();config.transactional_update(fixture('legacy-off'))
    proposal=propose_migration(config.data,SmartSettings(kind='personal'))
    binary=tmp_path/'old.exe';binary.write_bytes(b'fixture, never executed')
    receipt=commit_migration(config,proposal,previewed=True,binary_path=binary)
    if damage in ('binary','config'):
        (tmp_path/receipt[damage+'_backup']).write_bytes(b'corrupt fixture')
    if damage=='path':
        broken=dict(receipt,binary_backup='../outside.exe')
        config.set('migration_receipt',broken,False)
    if damage:
        with pytest.raises((OSError,ValueError)):verify_retained_migration_files(config)
    else:
        checked=verify_retained_migration_files(config)
        assert checked['bytes_verified'] and checked['source_revision']==proposal.source_revision
        assert checked['signature_verified'] is False and checked['activation_verified'] is False
        assert 'ipc_token' not in json.dumps(checked)


def test_failed_migration_commit_retains_legacy_and_reuses_verified_backup(tmp_path,monkeypatch):
    from config_manager import ConfigManager
    from smart_migration import commit_migration
    monkeypatch.setenv('NIGHT_LIGHT_BY_HT_CONFIG_DIR',str(tmp_path))
    config=ConfigManager();config.transactional_update(fixture('legacy-off'))
    proposal=propose_migration(config.data,SmartSettings(kind='personal'))
    binary=tmp_path/'fixture-old.exe';binary.write_bytes(b'fixture')
    before=config.file_path.read_bytes();old=dict(config.data)
    original=__import__('os').replace
    monkeypatch.setattr('config_manager.os.replace',lambda *a:(_ for _ in ()).throw(OSError('disk full')))
    with pytest.raises(OSError):commit_migration(config,proposal,previewed=True,binary_path=binary)
    assert config.file_path.read_bytes()==before and config.data==old
    backups=list(tmp_path.glob('config.pre-v2-*.json'))
    assert len(backups)==1 and backups[0].read_bytes()==before
    monkeypatch.setattr('config_manager.os.replace',original)
    commit_migration(config,proposal,previewed=True,binary_path=binary)
    assert len(list(tmp_path.glob('config.pre-v2-*.json')))==1


@pytest.mark.parametrize('kind,expected',[('pause','neutral_pause'),('adjustment','manual_hold')])
def test_switch_retains_unexpired_pause_or_hold_without_extending_it(kind,expected):
    from datetime import datetime,timezone
    source=fixture('legacy-learning')
    now=datetime(2026,9,9,22,tzinfo=timezone.utc)
    source.update(smart_hold_until=now.timestamp()+1200,smart_hold_kind=kind)
    proposal=propose_migration(source,SmartSettings(kind='personal'),now_utc=now)
    patch=migration_patch(source,proposal,choice='switch',previewed=True)
    override=patch['override_v2']
    assert override['kind']==expected
    assert datetime.fromisoformat(override['expiry_utc']).timestamp()==source['smart_hold_until']
    assert override['original_duration']==3600


def test_ambiguous_legacy_hold_cannot_be_silently_extended_or_dropped():
    source=fixture('legacy-learning');source['smart_hold_until']=1e12
    with pytest.raises(ValueError,match='clock'):
        propose_migration(source,SmartSettings(kind='personal'))
    proposal=propose_migration(source,SmartSettings(kind='personal'),clear_override=True)
    assert migration_patch(source,proposal,choice='switch',previewed=True)['override_v2'] is None


def test_corrupt_existing_backup_stops_migration_without_changing_source(tmp_path,monkeypatch):
    import hashlib
    from config_manager import ConfigManager
    from smart_migration import commit_migration
    monkeypatch.setenv('NIGHT_LIGHT_BY_HT_CONFIG_DIR',str(tmp_path))
    config=ConfigManager();config.transactional_update(fixture('legacy-off'))
    original=config.file_path.read_bytes()
    proposal=propose_migration(config.data,SmartSettings(kind='personal'))
    backup=tmp_path/f'config.pre-v2-{hashlib.sha256(original).hexdigest()}.json'
    backup.write_bytes(b'corrupt fixture')
    binary=tmp_path/'old-fixture.exe';binary.write_bytes(b'fixture')
    with pytest.raises(OSError,match='does not match'):
        commit_migration(config,proposal,previewed=True,binary_path=binary)
    assert config.file_path.read_bytes()==original and backup.read_bytes()==b'corrupt fixture'
