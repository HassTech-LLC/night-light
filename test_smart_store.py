"""Versioned saves use temporary config and a fake native display only."""
from dataclasses import replace
import pytest
from config_manager import ConfigManager
from smart_state import SmartSettings
from smart_store import SmartStore
from test_smart_runtime import runtime


@pytest.fixture
def stored(tmp_path,monkeypatch):
    monkeypatch.setenv('NIGHT_LIGHT_BY_HT_CONFIG_DIR',str(tmp_path))
    config=ConfigManager()
    config.transactional_update({'schema_version':2,'migration_state':'v2',
        'intent_v2':{'mode':'off','manual':{'warmth_kelvin':4000.,'dim_fraction':0.}},
        'ipc_token':'test-only-'+'x'*40,'theme':{'accent':'#123456'}})
    owner,e,backend,clock=runtime()
    owner.state=replace(owner.state,config_revision=config.get('config_revision'))
    return SmartStore(owner,config),owner,config,e,backend,clock


def save(store,owner,request='save1',settings=None):
    return store.save(settings or SmartSettings(kind='personal'),owner.state.config_revision,'session',request)


def test_save_commits_disk_before_runtime_and_preserves_unrelated_fields(stored,monkeypatch):
    store,owner,config,e,backend,clock=stored
    original=owner.accept_saved
    def observe(ticket,revision):
        assert config.get('intent_v2')['mode']=='smart'
        assert config.get('smart_settings_v2')==ticket.settings.to_dict()
        assert owner.state.mode=='off'
        original(ticket,revision)
    monkeypatch.setattr(owner,'accept_saved',observe)
    result=save(store,owner)
    assert result['outcome']=='saved' and owner.state.mode=='smart'
    assert config.get('theme')=={'accent':'#123456'}
    assert config.get('ipc_token')=='test-only-'+'x'*40
    assert 'ipc_token' not in str(result)


def test_failed_save_changes_neither_runtime_nor_disk(stored,monkeypatch):
    store,owner,config,e,backend,clock=stored
    old=owner.state;disk=config.file_path.read_bytes()
    monkeypatch.setattr('config_manager.os.replace',lambda *a:(_ for _ in ()).throw(OSError('full')))
    with pytest.raises(OSError):save(store,owner)
    assert owner.state==old and config.file_path.read_bytes()==disk


def test_new_off_while_staging_cancels_older_enable_before_disk_replace(stored,monkeypatch):
    store,owner,config,e,backend,clock=stored
    disk=config.file_path.read_bytes()
    original=__import__('os').fsync
    def interrupted(fd):
        original(fd)
        owner.command('off')
    monkeypatch.setattr('config_manager.os.fsync',interrupted)
    with pytest.raises(ValueError,match='changed'):save(store,owner)
    assert owner.state.mode=='off' and config.file_path.read_bytes()==disk


def test_replayed_saved_request_after_off_does_not_reenable_even_after_store_restart(stored):
    store,owner,config,e,backend,clock=stored
    first=save(store,owner)
    store.off()
    assert save(store,owner)==first and owner.state.mode=='off'
    again=SmartStore(owner,config)
    assert save(again,owner)==first and owner.state.mode=='off'
    with pytest.raises(ValueError,match='reused'):
        save(again,owner,settings=SmartSettings(kind='personal',warmth_kelvin=3000))


def test_off_remains_effective_when_persistence_fails(stored,monkeypatch):
    store,owner,config,e,backend,clock=stored
    save(store,owner)
    monkeypatch.setattr(config,'transactional_update',lambda *a,**k:(_ for _ in ()).throw(OSError('full')))
    result=store.off()
    assert result['outcome']=='off_not_saved' and owner.state.mode=='off' and not e.is_enabled


def test_legacy_configuration_requires_explicit_migration_before_v2_save(stored):
    store,owner,config,e,backend,clock=stored
    config.transactional_update({'migration_state':'legacy_pending'})
    with pytest.raises(ValueError,match='migration'):save(store,owner)


def test_save_during_tracking_preserves_position_and_velocity(stored):
    store,owner,config,e,backend,clock=stored
    save(store,owner)
    for _ in range(50):clock.advance(.1);owner.tick()
    old=owner.tracker
    save(store,owner,'save2',SmartSettings(kind='personal',warmth_kelvin=3000))
    assert owner.tracker.warmth.position==old.warmth.position
    assert owner.tracker.warmth.velocity==old.warmth.velocity


def test_saving_slower_brakes_continuously_then_adopts_new_policy(stored):
    store,owner,config,e,backend,clock=stored
    save(store,owner)
    for _ in range(100):clock.advance(.1);owner.tick()
    old=owner.tracker
    save(store,owner,'save2',SmartSettings(kind='personal',slower=.5))
    assert owner.tracker==old
    previous=old
    for _ in range(400):
        clock.advance(.1);owner.tick()
        current=owner.tracker
        assert abs(current.warmth.velocity-previous.warmth.velocity)<=old.warmth.policy.acceleration*.1+1e-12
        previous=current
    assert owner.tracker.slower==.5


def test_stale_revision_cannot_overwrite_other_writer(stored):
    store,owner,config,e,backend,clock=stored
    other=ConfigManager()
    other.transactional_update({'theme':'other writer'})
    disk=config.file_path.read_bytes()
    with pytest.raises(ValueError,match='changed'):save(store,owner)
    assert config.file_path.read_bytes()==disk and owner.state.mode=='off'


def test_saved_but_display_blocked_is_storage_success(stored):
    store,owner,config,e,backend,clock=stored
    e.set_windows_nightlight_policy(True)
    result=save(store,owner)
    assert result['outcome']=='saved' and owner.state.mode=='smart'
    assert owner.state.availability=='windows_on' and owner.tracker is None


def test_failed_frame_during_pace_change_does_not_spend_braking_time(stored):
    store,owner,config,e,backend,clock=stored
    save(store,owner)
    for _ in range(80):clock.advance(.1);owner.tick()
    save(store,owner,'save2',SmartSettings(kind='personal',slower=.5))
    before=owner.tracker;elapsed=owner._pace_elapsed
    backend.write_ok=False
    clock.advance(.1);owner.tick()
    assert owner.tracker==before and owner._pace_elapsed==elapsed


def test_owner_commits_reject_other_threads(stored):
    from concurrent.futures import ThreadPoolExecutor
    store,owner,config,e,backend,clock=stored
    with ThreadPoolExecutor(max_workers=1) as pool:
        with pytest.raises(RuntimeError,match='owner thread'):
            pool.submit(save,store,owner).result()


def test_neutral_daytime_runtime_can_finish_handoff(stored):
    store,owner,config,e,backend,clock=stored
    clock.utc=clock.utc.replace(hour=12)
    save(store,owner)
    for _ in range(30):clock.advance(.1);owner.tick()
    assert owner.tracker is not None and not owner.tracker.catching_up


def test_clock_failure_after_durable_save_is_not_reported_as_disk_failure(stored,monkeypatch):
    store,owner,config,e,backend,clock=stored
    monkeypatch.setattr(clock,'sample',lambda:(_ for _ in ()).throw(OSError('clock failed')))
    result=save(store,owner)
    assert result['outcome']=='saved' and config.get('intent_v2')['mode']=='smart'
    assert owner.tracker is None and owner.status.startswith('Clock unavailable')


def test_legacy_out_of_range_output_is_not_clamped_by_saving(stored):
    store,owner,config,e,backend,clock=stored
    e.temperature_k=1000
    assert e._apply_matrix(1,.3,0)
    before=len(backend.writes)
    result=save(store,owner)
    assert result['outcome']=='saved' and owner.tracker is None
    assert len(backend.writes)==before and 'confirmed starting' in owner.status
