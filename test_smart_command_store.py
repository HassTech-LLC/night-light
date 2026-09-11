"""Resident command persistence uses the same serialized worker as Save/Off."""
from datetime import timedelta
import pytest
from smart_store import AsyncSmartStore
from smart_state import Appearance
from test_smart_store import stored
from test_smart_async_store import settle


def test_manual_command_is_durable_without_replaying_on_poll(stored,monkeypatch):
    _,owner,config,engine,_,_=stored
    store=AsyncSmartStore(owner,config)
    try:
        store.submit_command('manual','session','manual',Appearance(3200,.12))
        assert owner.state.mode=='manual'
        settle(store)
        monkeypatch.setattr(owner,'command',lambda *a,**k:pytest.fail('Poll replayed a native command'))
        assert store.poll()[0]['outcome']=='command_saved'
        assert config.get('intent_v2')=={'mode':'manual','manual':{'warmth_kelvin':3200,'dim_fraction':.12}}
        assert not config.owner_commit_pending
    finally:store.close()


def test_slow_command_save_cannot_defeat_later_off(stored,monkeypatch):
    from threading import Event
    _,owner,config,engine,_,_=stored
    entered,release=Event(),Event()
    real=config.transactional_update_isolated
    def held(*args,**kwargs):
        entered.set()
        assert release.wait(5)
        return real(*args,**kwargs)
    monkeypatch.setattr(config,'transactional_update_isolated',held)
    store=AsyncSmartStore(owner,config)
    try:
        store.submit_command('manual','session','manual',Appearance(3200,.1))
        assert entered.wait(5)
        store.submit_off('session','off')
        assert owner.state.mode=='off' and not engine.is_enabled
        release.set();settle(store)
        assert [r['outcome'] for r in store.poll()]==['command_superseded','off_saved']
        assert config.get('intent_v2')['mode']=='off' and not config.owner_commit_pending
    finally:release.set();store.close()


def test_temporary_adjustment_survives_clean_restart_with_remaining_time(stored):
    from smart_runtime import NativeSmartRuntime
    _,owner,config,engine,_,clock=stored
    config.begin_session()
    store=AsyncSmartStore(owner,config)
    try:
        store.submit_command('smart','session','smart');settle(store);store.poll()
        store.submit_command('adjust','session','adjust',Appearance(3000,.1));settle(store);store.poll()
        original=owner.state.override
        config.finish_session()
        config.begin_session()
        restarted=NativeSmartRuntime.from_config(engine,config,clock)
        assert restarted.state.mode=='smart' and restarted.state.override==original
    finally:store.close()


def test_pause_keeps_original_expiry_and_resume_clears_it(stored):
    _,owner,config,_,_,_=stored
    store=AsyncSmartStore(owner,config)
    try:
        store.submit_command('smart','session','smart');settle(store);store.poll()
        store.submit_command('pause','session','pause');settle(store);store.poll()
        raw=config.get('override_v2')
        assert raw['kind']=='neutral_pause' and raw['appearance'] is None
        assert raw['expiry_utc']==(owner.last_sample.utc+timedelta(hours=1)).isoformat()
        restored=owner._restore_override(raw,owner.last_sample)
        assert restored==owner.state.override and not config.owner_commit_pending
        store.submit_command('resume','session','resume');settle(store);store.poll()
        assert config.get('override_v2') is None and not config.owner_commit_pending
    finally:store.close()


def test_failed_temporary_adjustment_is_not_mistaken_for_clean_saved_smart(stored,monkeypatch):
    _,owner,config,_,_,_=stored
    store=AsyncSmartStore(owner,config)
    try:
        store.submit_command('smart','session','smart');settle(store);store.poll()
        monkeypatch.setattr(config,'transactional_update_isolated',lambda *a,**k:(_ for _ in ()).throw(OSError('disk full')))
        store.submit_command('adjust','session','adjust',Appearance(3000,.1));settle(store)
        assert store.poll()[0]['outcome']=='command_not_saved'
        assert config.owner_commit_pending
    finally:store.close()


def test_duplicate_command_does_not_extend_pause_or_replay_after_off(stored):
    _,owner,config,_,_,_=stored
    store=AsyncSmartStore(owner,config)
    try:
        store.submit_command('smart','session','smart');settle(store);store.poll()
        store.submit_command('pause','session','pause');settle(store);store.poll()
        generation=owner.state.generation
        assert store.submit_command('pause','session','pause')['outcome']=='command_saved'
        assert owner.state.generation==generation
        store.submit_off('session','off');settle(store);store.poll()
        store.submit_command('pause','session','pause')
        assert owner.state.mode=='off'
        with pytest.raises(ValueError,match='reused'):
            store.submit_command('resume','session','pause')
    finally:store.close()
