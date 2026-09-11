"""Actual desktop methods with isolated adapters; never opens or installs an app."""
from types import SimpleNamespace
import pytest
import tray_app
from premium_ui import PremiumActions


@pytest.fixture
def app(monkeypatch):
    events=[]
    application=tray_app.TrayApp.__new__(tray_app.TrayApp)
    application._is_running=True
    application._migration=SimpleNamespace(done=False,result=None,
        off=lambda:events.append('off'),poll=lambda:events.append('poll'),close=lambda:events.append('close'))
    application.root=SimpleNamespace(after=lambda delay,callback:events.append(('timer',delay)),after_cancel=lambda token:events.append('cancel'))
    application.flyout=None
    application.smart=SimpleNamespace(enabled=True,tick=lambda:pytest.fail('Legacy scheduler ran during migration'),
        learner=SimpleNamespace(observe=lambda *args:pytest.fail('Legacy collection ran during migration')))
    application.events=events
    monkeypatch.setattr(tray_app,'config',SimpleNamespace(get=lambda *args:False))
    monkeypatch.setattr(tray_app,'engine',SimpleNamespace(reset_to_neutral=lambda:events.append('neutral')))
    return application


@pytest.mark.parametrize('method,args,expected',[
    ('toggle_nightlight',(),['off']),('_emergency_reset',(),['off']),
    ('apply_preset',(6500,),['off']),('apply_strength',(0,),['off']),
    ('apply_preset',(2800,),[]),('apply_strength',(70,),[]),('taskbar_smart',(False,),[])])
def test_tray_entry_points_obey_handoff_interlock(app,method,args,expected):
    getattr(app,method)(*args)
    assert app.events==expected


def test_tick_polls_without_legacy_scheduler_or_learning(app):
    app._tick_smart()
    assert app.events==['poll',('timer',100)]


@pytest.mark.parametrize('outcome',['migration_off_not_saved','migration_activation_failed'])
def test_failed_handoff_stays_interlocked_even_on_legacy_schema(app,outcome):
    app._migration.done=True
    app._migration.result={'outcome':outcome,'adopted':False}
    assert app.migration_interlocked()
    app._emergency_reset()
    assert app.events==['neutral']


def test_bridge_blocks_conflicting_actions_and_keeps_off(app):
    actions=PremiumActions(app,tray_app.engine,tray_app.config)
    with pytest.raises(ValueError,match='controls are paused'):
        actions.dispatch({'action':'adjust','kelvin':2800,'brightness':.8})
    actions.dispatch({'action':'off'})
    assert app.events==['off']


def test_preview_close_does_not_restore_legacy_snapshot(app):
    actions=PremiumActions(app,tray_app.engine,tray_app.config)
    actions.preview={'enabled':True,'temperature_k':2800,'brightness':.8}
    actions.end_preview()
    assert actions.preview is None and app.events==[]


def test_cleanup_does_not_wait_for_migration_storage(app):
    app.cleanup()
    assert app.events==['close']


def test_bridge_snapshot_explains_pending_handoff(app):
    actions=PremiumActions(app,tray_app.engine,tray_app.config)
    actions._snapshot_current=lambda:{'title':'Old status','times':{'start':'stale'}}
    state=actions.snapshot()
    assert state['migration_pending'] and state['times']=={}
    assert state['title']=='Switching Smart safely' and 'Off is still available' in state['detail']


def test_real_desktop_adopts_committed_controller_on_poll(tmp_path,monkeypatch):
    from config_manager import ConfigManager
    from nightlight_engine import NightLightEngine
    from smart_migration import propose_migration
    from smart_state import SmartSettings
    from smart_desktop import is_v2_controller
    monkeypatch.setenv('NIGHT_LIGHT_BY_HT_CONFIG_DIR',str(tmp_path/'settings'))
    config=ConfigManager()
    config.begin_session()
    engine=NightLightEngine()
    monkeypatch.setattr(tray_app,'config',config)
    monkeypatch.setattr(tray_app,'engine',engine)
    application=tray_app.TrayApp.__new__(tray_app.TrayApp)
    application._is_running=True
    application.root=SimpleNamespace(after=lambda *args:'timer',after_cancel=lambda *args:None)
    application.flyout=None;application.smart_window=None
    legacy=SimpleNamespace(hotkey_status='test hotkey',tick=lambda:pytest.fail('Old scheduler ran'))
    application.smart=legacy
    binary=tmp_path/'synthetic-never-executed.exe';binary.write_bytes(b'test previous binary')
    proposal=propose_migration(config.data,SmartSettings(kind='personal'))
    application.begin_smart_migration(proposal,binary)
    try:
        application._migration.future.result(timeout=3)
        assert application.smart is legacy
        application._tick_smart()
        assert is_v2_controller(application.smart)
        assert application.smart.owner.state.mode=='off'
        assert application.smart.hotkey_status=='test hotkey'
        assert not application.migration_interlocked()
    finally:
        if is_v2_controller(application.smart):application.smart.close()
        else:application._migration.close()
