from types import SimpleNamespace
import pytest
from test_smart_restart import saved
from test_smart_conflicts import setup
from test_smart_runtime import Clock
from test_smart_async_store import settle


def controller(saved):
    from smart_desktop import SmartDesktopController
    engine,_=setup()
    return SmartDesktopController(engine,saved,Clock())


def test_new_settings_save_is_pending_until_owner_completion(saved):
    from premium_ui import PremiumActions
    smart=controller(saved)
    actions=PremiumActions(SimpleNamespace(smart=smart),smart.owner.engine,saved)
    try:
        draft=smart.owner.state.settings.to_dict();draft['warmth_kelvin']=3200
        assert saved.get('onboarding_v2')['completed'] is False
        actions.dispatch({'action':'save_comfort','settings':draft,
                          'expected_revision':smart.owner.state.config_revision,'request_id':'save-new'})
        assert actions.snapshot()['save_result']['outcome']=='saving'
        assert smart.owner.state.mode=='off'
        settle(smart.store);smart.poll()
        assert actions.snapshot()['save_result']['outcome']=='saved'
        assert smart.owner.state.settings.warmth_kelvin==3200 and smart.enabled
        assert saved.get('onboarding_v2')['completed'] is True
    finally:smart.close()


def test_comfort_preview_does_not_enable_saved_mode_and_power_cancels_it(saved):
    from premium_ui import PremiumActions
    smart=controller(saved)
    actions=PremiumActions(SimpleNamespace(smart=smart),smart.owner.engine,saved)
    try:
        actions.dispatch({'action':'preview_comfort','warmth_kelvin':3200,'dim_fraction':.1})
        state=actions.snapshot()
        assert state['preview_kind']=='comfort' and state['preview_remaining']==20
        assert saved.get('intent_v2')['mode']=='off'
        actions.dispatch({'action':'power'});settle(smart.store);smart.poll()
        assert smart.owner.state.preview is None and smart.owner.state.mode=='off'
    finally:smart.close()


def test_tray_preset_uses_v2_owner_not_direct_legacy_engine(saved,monkeypatch):
    from tray_app import TrayApp
    smart=controller(saved)
    app=TrayApp.__new__(TrayApp);app.smart=smart;app.flyout=None;app.hud=None
    app.update_tray=lambda:None
    try:
        monkeypatch.setattr('tray_app.engine.set_state',lambda **k:pytest.fail('Legacy engine path'))
        app.apply_preset(3200)
        settle(smart.store);smart.poll()
        assert smart.owner.state.mode=='manual'
        assert saved.get('intent_v2')['manual']['warmth_kelvin']==3200
        app.apply_strength(0);settle(smart.store);smart.poll()
        assert smart.owner.state.mode=='off'
    finally:smart.close()


def test_v2_snapshot_reports_durable_reply_without_legacy_timeline(saved):
    from premium_ui import PremiumActions
    smart=controller(saved)
    actions=PremiumActions(SimpleNamespace(smart=smart),smart.owner.engine,saved)
    try:
        actions.dispatch({'action':'mode','mode':'smart'})
        settle(smart.store);smart.poll()
        state=actions.snapshot()
        assert state['command_result']['outcome']=='command_saved'
        assert state['smart_settings']==smart.owner.state.settings.to_dict()
        assert state['settings']['learning'] is False and state['times']['kind']=='Your schedule'
        assert state['times']['ready_utc']
        assert 'ipc_token' not in str(state)
    finally:smart.close()


def test_v2_emergency_off_uses_owner_and_removes_compare(saved):
    from tray_app import TrayApp
    smart=controller(saved)
    app=TrayApp.__new__(TrayApp);app.smart=smart;app.flyout=None;app.update_tray=lambda:None
    try:
        smart.command('smart');settle(smart.store);smart.poll()
        smart.owner.command('begin_compare',token='preview')
        app._emergency_reset();settle(smart.store);smart.poll()
        assert smart.owner.state.preview is None and smart.owner.state.mode=='off'
        assert saved.get('intent_v2')['mode']=='off'
    finally:smart.close()


def test_windows_clear_uses_owner_without_legacy_rejoin_animation(saved,monkeypatch):
    from tray_app import TrayApp
    from windows_nightlight import WindowsNightLightStatus
    smart=controller(saved);engine=smart.owner.engine
    app=TrayApp.__new__(TrayApp);app.smart=smart;app.flyout=None;app.update_tray=lambda:None
    app.windows_nightlight_status=WindowsNightLightStatus(True,'On')
    app.tray_icon=None;app._ensure_jumplist=lambda:None
    try:
        smart.command('smart');settle(smart.store);smart.poll()
        engine.set_windows_nightlight_policy(True);smart.tick()
        monkeypatch.setattr('tray_app.engine',engine)
        monkeypatch.setattr('tray_app.get_windows_nightlight_status',lambda:WindowsNightLightStatus(False,'Off'))
        monkeypatch.setattr(engine,'set_state',lambda **k:pytest.fail('Legacy rejoin animation'))
        app._refresh_windows_nightlight_policy(schedule_next=False)
        assert not engine.is_suppressed_by_windows_nightlight
        assert smart.owner.state.mode=='smart'
    finally:smart.close()


def test_premium_v2_actions_reach_same_owner_and_never_write_legacy_settings(saved):
    from premium_ui import PremiumActions
    smart=controller(saved)
    actions=PremiumActions(SimpleNamespace(smart=smart),smart.owner.engine,saved)
    try:
        actions.dispatch({'action':'mode','mode':'smart'})
        settle(smart.store);smart.poll()
        actions.dispatch({'action':'pause'})
        settle(smart.store);smart.poll()
        assert smart.owner.state.override.kind=='neutral_pause'
        assert not saved.get('smart_enabled')
        with pytest.raises(ValueError,match='updated Smart settings'):
            actions.dispatch({'action':'save_smart','profile':'maximum'})
        actions.dispatch({'action':'off'});settle(smart.store);smart.poll()
        assert smart.owner.state.mode=='off' and saved.get('intent_v2')['mode']=='off'
    finally:smart.close()


def test_v2_tick_does_not_sample_learning_and_uses_fast_owner_timer(saved,monkeypatch):
    from tray_app import TrayApp
    smart=controller(saved);timers=[]
    app=TrayApp.__new__(TrayApp);app.smart=smart;app._is_running=True
    app.flyout=None;app.tray_icon=None;app.root=SimpleNamespace(after=lambda *a:timers.append(a))
    app.update_tray=lambda:None
    try:
        monkeypatch.setattr('tray_app.idle_seconds',lambda:pytest.fail('v2 collected idle time'))
        monkeypatch.setattr('tray_app.high_contrast_active',lambda:False)
        app._tick_smart()
        assert timers[-1][0]==100
    finally:smart.close()
