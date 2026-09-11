"""Event-controlled worker tests: no sleeps, live settings or display backend."""
from threading import Event, get_ident
import pytest
from smart_store import AsyncSmartStore
from smart_state import SmartSettings
from test_smart_store import stored


def settle(store):
    # A queued barrier proves every preceding disk operation is terminal.
    store._worker.submit(lambda:None).result(timeout=5)


def test_slow_disk_does_not_block_off_and_cannot_reenable_after_completion(stored,monkeypatch):
    _,owner,config,e,backend,clock=stored
    entered,release=Event(),Event()
    fsync=__import__('os').fsync
    def held(fd):
        fsync(fd);entered.set()
        assert release.wait(5)
    monkeypatch.setattr('config_manager.os.fsync',held)
    store=AsyncSmartStore(owner,config)
    try:
        store.submit_save(SmartSettings(kind='personal'),owner.state.config_revision,'session','save')
        assert entered.wait(5)
        assert config.get('smart_settings_v2') is None  # Staging is private to worker.
        store.submit_off('session','off')
        assert owner.state.mode=='off' and not e.is_enabled and not release.is_set()
        release.set()
        settle(store)
        results=store.poll()
        assert {r['outcome'] for r in results}=={'save_superseded','off_saved'}
        assert config.get('intent_v2')['mode']=='off' and owner.state.mode=='off'
    finally:
        release.set();store.close()


def test_native_commit_only_occurs_when_owner_polls(stored,monkeypatch):
    _,owner,config,e,backend,clock=stored
    main_thread=get_ident();called=[]
    accept=owner.accept_saved
    def checked(*args):
        called.append(get_ident());assert get_ident()==main_thread
        accept(*args)
    monkeypatch.setattr(owner,'accept_saved',checked)
    store=AsyncSmartStore(owner,config)
    try:
        store.submit_save(SmartSettings(kind='personal'),owner.state.config_revision,'session','save')
        settle(store)
        assert not called and owner.state.mode=='off'
        assert store.poll()[0]['outcome']=='saved'
        assert called==[main_thread] and owner.state.mode=='smart'
    finally:store.close()


def test_save_finished_on_disk_but_new_off_before_poll_wins(stored):
    _,owner,config,e,backend,clock=stored
    store=AsyncSmartStore(owner,config)
    try:
        store.submit_save(SmartSettings(kind='personal'),owner.state.config_revision,'session','save')
        settle(store)
        assert config.get('intent_v2')['mode']=='smart' and owner.state.mode=='off'
        store.submit_off('session','off')
        settle(store)
        results=store.poll()
        assert results[0]['outcome']=='save_superseded' and results[0]['persisted']
        assert owner.state.mode=='off' and config.get('intent_v2')['mode']=='off'
    finally:store.close()


def test_async_duplicate_pending_request_does_not_write_twice(stored):
    _,owner,config,e,backend,clock=stored
    store=AsyncSmartStore(owner,config)
    try:
        old=owner.state.config_revision
        first=store.submit_save(SmartSettings(kind='personal'),old,'session','save')
        again=store.submit_save(SmartSettings(kind='personal'),old,'session','save')
        assert first==again
        with pytest.raises(ValueError,match='reused'):
            store.submit_save(SmartSettings(kind='personal',warmth_kelvin=3200),old,'session','save')
        settle(store)
        assert len(store.poll())==1 and config.get('config_revision')==old+1
    finally:store.close()


def test_failed_off_persistence_cannot_close_recovery_receipt(stored,monkeypatch):
    import json
    _,owner,config,e,backend,clock=stored
    config.begin_session()
    store=AsyncSmartStore(owner,config)
    try:
        store.submit_save(SmartSettings(kind='personal'),owner.state.config_revision,'session','save')
        settle(store);store.poll()
        monkeypatch.setattr(config,'transactional_update_isolated',lambda *a,**k:(_ for _ in ()).throw(OSError('disk full')))
        store.submit_off('session','off')
        settle(store)
        assert store.poll()[0]['outcome']=='off_not_saved'
        assert owner.state.mode=='off' and config.owner_commit_pending
        with pytest.raises(OSError,match='not durably confirmed'):config.finish_session()
        assert json.loads(config.file_path.with_name('session-recovery.json').read_text())['state']=='open'
    finally:store.close()


def test_retry_off_reconciles_failed_write_and_allows_clean_shutdown(stored,monkeypatch):
    _,owner,config,e,backend,clock=stored
    config.begin_session()
    store=AsyncSmartStore(owner,config)
    try:
        store.submit_save(SmartSettings(kind='personal'),owner.state.config_revision,'session','save')
        settle(store);store.poll()
        real=config.transactional_update_isolated
        monkeypatch.setattr(config,'transactional_update_isolated',lambda *a,**k:(_ for _ in ()).throw(OSError('disk full')))
        store.submit_off('session','off1');settle(store);store.poll()
        monkeypatch.setattr(config,'transactional_update_isolated',real)
        store.submit_off('session','off2');settle(store)
        assert store.poll()[0]['outcome']=='off_saved' and not config.owner_commit_pending
        config.finish_session()
    finally:store.close()


def test_failed_async_save_never_exposes_draft_or_changes_native_state(stored,monkeypatch):
    _,owner,config,e,backend,clock=stored
    original=config.file_path.read_bytes()
    monkeypatch.setattr('config_manager.os.replace',lambda *a:(_ for _ in ()).throw(OSError('disk full')))
    store=AsyncSmartStore(owner,config)
    try:
        store.submit_save(SmartSettings(kind='personal'),owner.state.config_revision,'session','save')
        settle(store)
        assert store.poll()[0]['outcome']=='save_failed'
        assert config.get('smart_settings_v2') is None and owner.state.mode=='off'
        assert config.file_path.read_bytes()==original and not config.owner_commit_pending
    finally:store.close()
