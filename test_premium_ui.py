from types import SimpleNamespace
import pytest
from premium_ui import PremiumActions, number
from config_manager import ConfigManager
from nightlight_engine import NightLightEngine
from smart_mode import SmartController

@pytest.fixture
def actions(tmp_path,monkeypatch):
    monkeypatch.setenv('NIGHT_LIGHT_BY_HT_CONFIG_DIR',str(tmp_path))
    c=ConfigManager();e=NightLightEngine();s=SmartController(e,c)
    app=SimpleNamespace(smart=s,_get_display_status=lambda:SimpleNamespace(detail='Test'),turn_windows_nightlight_off=lambda:None)
    return PremiumActions(app,e,c)

@pytest.mark.parametrize('value',[float('nan'),float('inf'),-1,101,True,None,'oops'])
def test_number_rejects_unsafe_values(value):
    with pytest.raises((ValueError,TypeError)):number(value,0,100)

def test_adjust_hold_and_real_engine_state(actions):
    actions.config.set('smart_enabled',True)
    actions.dispatch({'action':'adjust','kelvin':3200,'brightness':.72})
    assert actions.engine.temperature_k==3200
    assert actions.engine.brightness==.72
    assert actions.engine.is_enabled
    assert actions.snapshot()['hold']
    assert actions.config.get('temperature_k')==3200

def test_compare_restores_without_changing_preferences(actions):
    actions.dispatch({'action':'adjust','kelvin':4200,'brightness':.8})
    before=dict(actions.config.data)
    actions.dispatch({'action':'compare','enabled':True})
    assert not actions.engine.is_enabled
    actions.dispatch({'action':'compare','enabled':False})
    assert actions.engine.is_enabled and actions.engine.temperature_k==4200
    assert actions.config.data==before

def test_off_during_compare_cannot_restore_filter(actions):
    actions.dispatch({'action':'adjust','kelvin':3200,'brightness':.7})
    actions.dispatch({'action':'compare','enabled':True})
    actions.dispatch({'action':'off'})
    actions.end_preview()
    assert not actions.engine.is_enabled and not actions.app.smart.enabled

def test_save_validation_is_atomic(actions):
    before=dict(actions.config.data)
    with pytest.raises(ValueError):actions.dispatch({'action':'save_smart','profile':'balanced','latitude':'42','longitude':'-83','bedtime':'invalid'})
    assert before==actions.config.data

def test_setup_pause_resume_manual(actions):
    actions.dispatch({'action':'save_smart','profile':'balanced','latitude':'42.3353','longitude':'-83.2864'})
    assert actions.app.smart.enabled
    assert actions.snapshot()['times']['start']
    actions.dispatch({'action':'pause'})
    assert not actions.engine.is_enabled and actions.snapshot()['hold']
    actions.dispatch({'action':'resume'})
    assert not actions.snapshot()['hold']
    actions.dispatch({'action':'mode','mode':'manual'})
    assert not actions.app.smart.enabled

def test_snapshot_never_discloses_ipc_or_history(actions):
    actions.config.set('ipc_token','private-test')
    actions.config.set('smart_nights',[{'private':'history'}])
    import json
    output=json.dumps(actions.snapshot())
    assert 'private-test' not in output and 'history' not in output

@pytest.mark.parametrize('data',[{},[],{'action':'exec'},{'action':'adjust','kelvin':0,'brightness':1},{'action':'learning','enabled':'yes'}])
def test_bridge_rejects_unknown_or_malformed_actions(actions,data):
    with pytest.raises((ValueError,TypeError)):actions.dispatch(data)

def test_save_confirmation_follows_disk_persistence(actions):
    import json
    message=actions.dispatch({'action':'save_smart','profile':'balanced','latitude':'42.3353','longitude':'-83.2864'})
    saved=json.loads(actions.config.file_path.read_text())
    assert saved['smart_enabled'] is True
    assert saved['smart_location']['latitude']==42.3353
    assert message.startswith('Saved.')

def test_failed_save_does_not_activate_or_mutate_settings(actions,monkeypatch):
    before=dict(actions.config.data)
    disk=actions.config.file_path.read_bytes()
    calls=[]
    monkeypatch.setattr(actions.engine,'set_state',lambda **kwargs:calls.append(kwargs))
    monkeypatch.setattr(actions.config,'_save_locked',lambda:(_ for _ in ()).throw(OSError('disk unavailable')))
    with pytest.raises(OSError):
        actions.dispatch({'action':'save_smart','profile':'balanced','latitude':'42','longitude':'-83'})
    assert actions.config.data==before
    assert actions.config.file_path.read_bytes()==disk
    assert not calls

def test_off_during_compare_does_not_briefly_reapply_filter(actions,monkeypatch):
    actions.dispatch({'action':'adjust','kelvin':3200,'brightness':.7})
    actions.dispatch({'action':'compare','enabled':True})
    calls=[]
    monkeypatch.setattr(actions.engine,'set_state',lambda **kwargs:calls.append(kwargs))
    actions.dispatch({'action':'off'})
    assert not any(call.get('enabled') for call in calls)

def test_retried_save_cannot_undo_later_off(actions):
    request={'action':'save_smart','session_id':actions.session_id,'request_id':'retry-1',
             'profile':'balanced','latitude':'42','longitude':'-83'}
    first=actions.dispatch(request)
    actions.dispatch({'action':'off'})
    revision=actions.config.get('config_revision')
    assert actions.dispatch(request)==first
    assert not actions.app.smart.enabled
    assert actions.config.get('config_revision')==revision

def test_request_id_cannot_be_reused_for_different_draft(actions):
    request={'action':'save_smart','session_id':actions.session_id,'request_id':'same',
             'profile':'balanced','latitude':'42','longitude':'-83'}
    actions.dispatch(request)
    with pytest.raises(ValueError,match='different'):
        actions.dispatch({**request,'profile':'maximum'})

def test_old_session_cannot_mutate_but_off_remains_available(actions):
    with pytest.raises(ValueError,match='session'):
        actions.dispatch({'action':'mode','mode':'smart','session_id':'old'})
    actions.dispatch({'action':'off','session_id':'old'})
    assert not actions.app.smart.enabled

@pytest.mark.parametrize('extra',[{'protocol_version':True},{'protocol_version':999},{'unexpected':'ignored-before'}, {'session_id':[]}])
def test_bridge_rejects_invalid_envelope(actions,extra):
    with pytest.raises((ValueError,TypeError)):
        actions.dispatch({'action':'state',**extra})

def test_off_storage_failure_does_not_prevent_neutral_intent(actions,monkeypatch):
    actions.dispatch({'action':'save_smart','profile':'balanced','latitude':'42','longitude':'-83'})
    monkeypatch.setattr(actions.config,'_save_locked',lambda:(_ for _ in ()).throw(OSError('disk full')))
    message=actions.dispatch({'action':'off'})
    assert not actions.engine.is_enabled and not actions.app.smart.enabled
    assert "Couldn't save this for next startup" in message
    if actions.config._debounce_timer:
        actions.config._debounce_timer.cancel()

def test_disk_failure_returns_correlated_error_and_poll_survives(actions,monkeypatch):
    import queue
    from premium_ui import PremiumFlyout
    callbacks=[];sent=[]
    actions.app.root=SimpleNamespace(after=lambda *args:callbacks.append(args))
    flyout=PremiumFlyout(actions.app,actions.engine,actions.config)
    monkeypatch.setattr(flyout,'_send',sent.append)
    monkeypatch.setattr(actions.config,'_save_locked',lambda:(_ for _ in ()).throw(OSError('disk unavailable')))
    flyout.messages.put({'action':'save_smart','request_id':'test-save','profile':'balanced','latitude':'42','longitude':'-83'})
    flyout._poll()
    assert sent[-1]['kind']=='error' and sent[-1]['request_id']=='test-save'
    assert 'Could not save' in sent[-1]['message']
    assert callbacks[-1][0]==40
    if actions.config._debounce_timer:
        actions.config._debounce_timer.cancel()

def test_taskbar_commands_are_explicit_and_default_opens():
    from main import command_from_args
    assert command_from_args([])=='SHOW'
    assert command_from_args(['--toggle'])=='TOGGLE'
    assert command_from_args(['--pause-smart'])=='PAUSE_SMART'
    assert command_from_args(['--resume-smart'])=='RESUME_SMART'

def test_open_command_never_hides_an_already_visible_window():
    from tray_app import TrayApp
    calls=[]
    app=SimpleNamespace(flyout=SimpleNamespace(winfo_viewable=lambda:True,hide_flyout=lambda:calls.append('hide'),show_flyout_at_tray=lambda:calls.append('show')))
    TrayApp.show_flyout(app)
    assert calls==['show']


def test_premium_host_uses_per_monitor_v2_before_creating_winforms():
    from pathlib import Path
    source=Path('premium_host.cs').read_text(encoding='utf-8')
    awareness=source.index('SetProcessDpiAwarenessContext(new IntPtr(-4))')
    visual_styles=source.index('Application.EnableVisualStyles()')
    assert awareness < visual_styles

def test_taskbar_pause_resume_and_stale_manual_command(actions):
    from tray_app import TrayApp
    calls=[]
    app=actions.app
    app.migration_interlocked=lambda:False
    app.flyout=SimpleNamespace(actions=actions,update_ui_state=lambda:calls.append('ui'))
    app.update_tray=lambda:calls.append('tray')
    app.show_flyout=lambda:calls.append('open')
    actions.dispatch({'action':'save_smart','profile':'balanced','latitude':'42','longitude':'-83'})
    TrayApp.taskbar_smart(app,True)
    assert actions.snapshot()['hold'] and not actions.engine.is_enabled
    TrayApp.taskbar_smart(app,False)
    assert not actions.snapshot()['hold']
    actions.app.smart.manual(reset=True)
    TrayApp.taskbar_smart(app,False)
    assert calls[-1]=='open' and not actions.app.smart.enabled


def test_retry_control_preserves_off_and_rejects_foreign_output(actions):
    from test_smart_conflicts import MatrixBackend,identity
    e=actions.engine;backend=MatrixBackend()
    e._mag=backend;e._mag_available=True;e._mag_initialized=True;e._readback_supported=True
    foreign=list(identity());foreign[0]=.7;backend.matrix=tuple(foreign)
    e.refresh_output_observation()
    snapshot=actions.snapshot()
    assert snapshot['output_fault']=='external_conflict'
    assert 'changed' in snapshot['title'].lower()
    with pytest.raises(ValueError,match='display transform'):
        actions.dispatch({'action':'retry_display'})
    assert not backend.writes
    backend.matrix=identity()
    result=actions.dispatch({'action':'retry_display'})
    assert 'off' in result.lower() and not e.is_enabled and not actions.app.smart.enabled


def test_retry_control_resumes_manual_only_after_explicit_request(actions):
    from test_smart_conflicts import MatrixBackend,identity
    e=actions.engine;backend=MatrixBackend()
    e._mag=backend;e._mag_available=True;e._mag_initialized=True;e._readback_supported=True
    actions.dispatch({'action':'adjust','kelvin':3500,'brightness':.7})
    foreign=list(identity());foreign[0]=.7;backend.matrix=tuple(foreign)
    e.refresh_output_observation()
    before=len(backend.writes)
    backend.matrix=identity()
    e.refresh_output_observation()
    assert len(backend.writes)==before and e.output_fault=='external_conflict'
    actions.dispatch({'action':'retry_display'})
    assert e.output_fault is None and e.is_enabled and e.is_applied
    assert e.temperature_k==3500 and e.brightness==.7


@pytest.mark.parametrize('pause',[True,False])
def test_retry_keeps_smart_override_and_original_expiry(actions,pause):
    from test_smart_conflicts import MatrixBackend
    e=actions.engine;backend=MatrixBackend()
    e._mag=backend;e._mag_available=True;e._mag_initialized=True;e._readback_supported=True
    actions.config.set('smart_enabled',True)
    if pause:actions.dispatch({'action':'pause'})
    else:actions.dispatch({'action':'adjust','kelvin':3500,'brightness':.7})
    expiry=actions.config.get('smart_hold_until')
    backend.read_ok=False;e.refresh_output_observation();backend.read_ok=True
    actions.dispatch({'action':'retry_display'})
    assert actions.config.get('smart_hold_until')==expiry
    assert actions.app.smart.enabled and e.is_enabled is not pause
    if not pause:assert e.temperature_k==3500 and e.brightness==.7


def test_retry_display_does_not_bypass_recovery_storage_block(actions,monkeypatch):
    from test_smart_conflicts import MatrixBackend
    e=actions.engine;backend=MatrixBackend()
    e._mag=backend;e._mag_available=True;e._mag_initialized=True;e._readback_supported=True
    actions.config.set('smart_enabled',True)
    actions.config.automatic_output_blocked=True
    calls=[]
    monkeypatch.setattr(actions.app.smart,'tick',lambda:calls.append('automatic'))
    result=actions.dispatch({'action':'retry_display'})
    assert not calls and not e.is_enabled
    assert 'remains stopped' in result
