from threading import Event, get_ident
from types import SimpleNamespace
import pytest
from smart_migration_switch import MigrationSwitch


class Config:
    def __init__(self):
        self.data={}
        self.owner_commit_pending=False
        self.fail_off=False
    def get(self,key,default=None):return self.data.get(key,default)
    def off_patch(self):return {'intent_v2':{'mode':'off'}}
    def transactional_update_isolated(self,patch):
        if self.fail_off:raise OSError('private path must not escape')
        self.data.update(patch)


def setup(commit):
    config=Config();events=[]
    engine=SimpleNamespace(reset_to_neutral=lambda:events.append(('neutral',get_ident())))
    switch=MigrationSwitch(config,engine,None,None,
        lambda:events.append(('adopt',config.get('intent_v2'),get_ident())),commit=commit)
    return switch,config,events


def committed(config,*args,**kwargs):
    kwargs['before_commit']()
    config.data.update(schema_version=2,migration_state='v2',intent_v2={'mode':'smart'})


def test_success_adopts_only_when_gui_polls():
    switch,config,events=setup(committed)
    switch.future.result(timeout=3)
    assert events==[] and config.owner_commit_pending
    assert switch.poll()=={'outcome':'migrated','adopted':True}
    assert events==[('adopt',{'mode':'smart'},get_ident())]
    assert not config.owner_commit_pending


def test_off_after_commit_before_poll_never_adopts_smart():
    switch,config,events=setup(committed)
    switch.future.result(timeout=3)
    switch.off()
    assert events==[('neutral',get_ident())]
    switch.off_future.result(timeout=3)
    assert switch.poll()['outcome']=='migration_off'
    assert events[-1]==('adopt',{'mode':'off'},get_ident())


def test_off_cancels_pending_commit_without_waiting_for_storage():
    entered=Event();release=Event()
    def paused(config,*args,**kwargs):
        entered.set()
        assert release.wait(3)
        committed(config,*args,**kwargs)
    switch,config,events=setup(paused)
    try:
        assert entered.wait(3)
        switch.off()
        assert events==[('neutral',get_ident())] and switch.poll() is None
    finally:release.set()
    switch.off_future.result(timeout=3)
    assert switch.poll()=={'outcome':'migration_off','adopted':False}


def test_off_persistence_failure_never_adopts_and_keeps_recovery_open():
    switch,config,events=setup(committed)
    switch.future.result(timeout=3)
    config.fail_off=True
    switch.off()
    with pytest.raises(OSError):switch.off_future.result(timeout=3)
    result=switch.poll()
    assert result=={'outcome':'migration_off_not_saved','adopted':False}
    assert config.owner_commit_pending and not any(e[0]=='adopt' for e in events)
    assert 'private' not in str(result)


def test_adoption_failure_keeps_recovery_open_and_requests_neutral():
    switch,config,events=setup(committed)
    switch.future.result(timeout=3)
    def broken():raise RuntimeError('private detail')
    switch.adopt=broken
    assert switch.poll()=={'outcome':'migration_activation_failed','adopted':False}
    assert config.owner_commit_pending and events[-1][0]=='neutral'


def test_adopted_controller_can_keep_recovery_open():
    switch,config,events=setup(committed)
    switch.future.result(timeout=3)
    switch.adopt=lambda:setattr(config,'owner_commit_pending',True)
    switch.poll()
    assert config.owner_commit_pending


def test_real_private_transaction_retains_settings_and_adopts_off(tmp_path,monkeypatch):
    from config_manager import ConfigManager
    from smart_migration import propose_migration,verify_retained_migration_files
    from smart_state import SmartSettings
    monkeypatch.setenv('NIGHT_LIGHT_BY_HT_CONFIG_DIR',str(tmp_path/'config'))
    config=ConfigManager()
    config.transactional_update({'enabled':False,'smart_enabled':False,'custom_theme':'saved-color'})
    proposal=propose_migration(config.data,SmartSettings(kind='personal'))
    binary=tmp_path/'synthetic-never-executed.exe'
    binary.write_bytes(b'synthetic previous application')
    seen=[]
    engine=SimpleNamespace(reset_to_neutral=lambda:seen.append('neutral'))
    switch=MigrationSwitch(config,engine,proposal,binary,
                           lambda:seen.append(config.get('intent_v2')['mode']))
    switch.future.result(timeout=3)
    assert seen==[]
    assert switch.poll()=={'outcome':'migrated','adopted':True}
    assert seen==['off'] and config.get('custom_theme')=='saved-color'
    assert verify_retained_migration_files(config)['bytes_verified']
