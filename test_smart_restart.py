from dataclasses import replace
from datetime import datetime,timedelta,timezone
import pytest
from config_manager import ConfigManager
from smart_migration import new_install_patch
from smart_runtime import NativeSmartRuntime
from smart_state import SmartSettings
from test_smart_runtime import Clock
from test_smart_conflicts import setup


@pytest.fixture
def saved(tmp_path,monkeypatch):
    monkeypatch.setenv('NIGHT_LIGHT_BY_HT_CONFIG_DIR',str(tmp_path))
    config=ConfigManager();config.transactional_update(new_install_patch())
    assert config.begin_session()
    return config


def restore(config,clock=None):
    engine,backend=setup()
    return NativeSmartRuntime.from_config(engine,config,clock or Clock()),engine,backend


def test_off_restart_stays_neutral_and_does_not_start_automatic_motion(saved):
    owner,e,backend=restore(saved)
    assert owner.state.mode=='off' and owner.tracker is None and not e.is_enabled
    assert e.output_observation()['accepted_rgb']==[1,1,1]


def test_smart_restart_restores_explicit_settings_not_legacy_flags(saved):
    settings=SmartSettings(kind='personal',warmth_kelvin=3200,dim_fraction=.15)
    saved.transactional_update({'intent_v2':{'mode':'smart','manual':{'warmth_kelvin':4500,'dim_fraction':.05}},
                                'smart_settings_v2':settings.to_dict(),'enabled':False,'smart_enabled':False})
    clock=Clock();owner,e,backend=restore(saved,clock)
    assert owner.state.mode=='smart' and owner.state.settings==settings
    assert owner.tracker is not None and owner.tracker.warmth.position==0
    clock.advance(.1);owner.tick()
    assert 0<owner.tracker.warmth.position<1/1024


def test_manual_restart_requests_only_valid_saved_appearance(saved):
    saved.transactional_update({'intent_v2':{'mode':'manual','manual':{'warmth_kelvin':4200,'dim_fraction':.1}}})
    owner,e,backend=restore(saved)
    assert owner.state.mode=='manual' and e.temperature_k==4200 and e.brightness==pytest.approx(.9)
    assert e.is_applied and e.is_enabled


def test_manual_restart_under_windows_suppression_waits_for_retry(saved):
    saved.transactional_update({'intent_v2':{'mode':'manual','manual':{'warmth_kelvin':4200,'dim_fraction':.1}}})
    e,backend=setup();e.set_windows_nightlight_policy(True)
    owner=NativeSmartRuntime.from_config(e,saved,Clock())
    assert owner.state.manual_resume_required and not e.is_enabled
    e.set_windows_nightlight_policy(False);owner.tick()
    assert owner.state.manual_resume_required and not e.is_enabled


def test_pause_restart_preserves_only_remaining_duration(saved):
    clock=Clock();now=clock.utc
    saved.transactional_update({'intent_v2':{'mode':'smart','manual':{'warmth_kelvin':4000,'dim_fraction':0}},
        'override_v2':{'kind':'neutral_pause','original_duration':3600,
                      'start_utc':(now-timedelta(minutes=40)).isoformat(),
                      'expiry_utc':(now+timedelta(minutes=20)).isoformat(),
                      'last_seen_utc':now.isoformat(),'appearance':None}})
    owner,e,backend=restore(saved,clock)
    assert owner.state.override.expires_elapsed==clock.elapsed+1200
    assert owner.tracker is None and not e.is_enabled
    clock.advance(1201,sleep=True);owner.tick()
    assert owner.state.override is None and owner.tracker.warmth.position==0


@pytest.mark.parametrize('patch',[{'intent_v2':{'mode':'invalid'}},
    {'smart_settings_v2':{'kind':'personal','warmth_kelvin':99999}},
    {'override_v2':{'kind':'manual_hold','original_duration':999999}}])
def test_invalid_saved_v2_data_fails_neutral_and_requires_repair(saved,patch):
    saved.transactional_update(patch)
    owner,e,backend=restore(saved)
    assert owner.state.mode=='off' and not e.is_enabled
    assert 'repair' in owner.status.lower() and saved.owner_commit_pending


def test_unclean_restart_cannot_restore_previous_smart_intent(saved):
    saved.transactional_update({'intent_v2':{'mode':'smart','manual':{'warmth_kelvin':4000,'dim_fraction':0}}})
    restarted=ConfigManager();assert restarted.begin_session()
    owner,e,backend=restore(restarted)
    assert restarted.recovered_unclean_session and owner.state.mode=='off' and not e.is_enabled


def test_missing_recovery_session_prevents_automated_start(saved):
    saved.transactional_update({'intent_v2':{'mode':'smart','manual':{'warmth_kelvin':4000,'dim_fraction':0}}})
    saved.session_id=None
    owner,e,backend=restore(saved)
    assert owner.state.mode=='off' and not e.is_enabled
    assert 'recovery' in owner.status.lower()


def test_legacy_emergency_off_requests_neutral_before_any_config_lock():
    from smart_mode import SmartController
    class Engine:
        is_enabled=True
        def reset_to_neutral(self):self.is_enabled=False
    engine=Engine()
    class Config(dict):
        def set(self,*args,**kwargs):
            assert not engine.is_enabled
            raise OSError('settings unavailable')
    controller=SmartController(engine,Config())
    with pytest.raises(OSError):controller.manual(reset=True)
    assert not engine.is_enabled


def test_foreign_transform_on_restart_is_not_overwritten(saved):
    saved.transactional_update({'intent_v2':{'mode':'smart','manual':{'warmth_kelvin':4000,'dim_fraction':0}}})
    e,backend=setup();matrix=list(backend.matrix);matrix[1]=.2;backend.matrix=tuple(matrix)
    owner=NativeSmartRuntime.from_config(e,saved,Clock())
    assert owner.state.availability=='external_conflict' and owner.tracker is None
    assert not backend.writes


def test_temporary_manual_restart_restores_hold_not_permanent_manual(saved):
    clock=Clock();now=clock.utc
    saved.transactional_update({'intent_v2':{'mode':'smart','manual':{'warmth_kelvin':4000,'dim_fraction':0}},
        'override_v2':{'kind':'manual_hold','original_duration':3600,
                      'start_utc':(now-timedelta(minutes=40)).isoformat(),
                      'expiry_utc':(now+timedelta(minutes=20)).isoformat(),
                      'last_seen_utc':now.isoformat(),
                      'appearance':{'warmth_kelvin':4500,'dim_fraction':.1}}})
    owner,e,backend=restore(saved,clock)
    assert owner.state.mode=='smart' and owner.state.override.kind=='manual_hold'
    assert e.temperature_k==4500 and owner.tracker is None


def test_clock_rollback_does_not_extend_a_persisted_pause(saved):
    clock=Clock();now=clock.utc
    saved.transactional_update({'intent_v2':{'mode':'smart','manual':{'warmth_kelvin':4000,'dim_fraction':0}},
        'override_v2':{'kind':'neutral_pause','original_duration':3600,
                      'start_utc':now.isoformat(),
                      'expiry_utc':(now+timedelta(hours=1)).isoformat(),
                      'last_seen_utc':(now+timedelta(minutes=10)).isoformat(),'appearance':None}})
    owner,e,backend=restore(saved,clock)
    assert owner.state.override is None and owner.tracker.warmth.position==0


def test_async_save_clean_shutdown_and_new_owner_restore_same_explicit_preferences(saved):
    from smart_store import AsyncSmartStore
    owner,e,backend=restore(saved)
    settings=SmartSettings(kind='personal',evening_ready='21:30',morning_neutral='06:45',
                           warmth_kelvin=3600,dim_fraction=.07,slower=.5)
    store=AsyncSmartStore(owner,saved)
    try:
        store.submit_save(settings,owner.state.config_revision,'fixture-session','save')
        store._worker.submit(lambda:None).result(timeout=5)
        assert store.poll()[0]['outcome']=='saved'
        assert not saved.owner_commit_pending
    finally:store.close()
    e.reset_to_neutral()
    saved.finish_session()
    restarted=ConfigManager();assert restarted.begin_session()
    again,new_engine,new_backend=restore(restarted)
    assert not restarted.recovered_unclean_session
    assert again.state.mode=='smart' and again.state.settings==settings
    assert again.state.owner_id!=owner.state.owner_id
    assert again.tracker.warmth.position==0 and new_engine.output_observation()['accepted_rgb']==[1,1,1]
