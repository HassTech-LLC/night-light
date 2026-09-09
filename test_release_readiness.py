"""Release regressions: isolated config/backend, no production integration."""
import os
import subprocess
import sys


def test_command_entry_import_does_not_load_display_engine():
    result = subprocess.run([sys.executable, '-c',
        'import main, sys; assert "nightlight_engine" not in sys.modules; assert "tray_app" not in sys.modules'],
        capture_output=True, text=True, env=os.environ.copy())
    assert result.returncode == 0, result.stderr


def test_ownership_is_attempted_before_dispatch_and_denial_fails_closed(monkeypatch):
    import main
    import ipc_transport
    events = []
    def unavailable():
        events.append('ownership')
        raise OSError('occupied')
    monkeypatch.setattr(ipc_transport, 'reserve_listener', unavailable)
    monkeypatch.setattr(main, 'send_ipc_command', lambda command: events.append('dispatch-denied') or False)
    monkeypatch.setattr(sys, 'argv', ['main.py', '--background'])
    with pytest.raises(SystemExit):
        main.main()
    assert events == ['ownership', 'dispatch-denied']


def test_occupied_endpoint_never_constructs_resident(monkeypatch):
    import socket
    import types
    import main
    import ipc_transport
    calls = []
    with socket.socket() as occupied:
        occupied.bind(('127.0.0.1', 0))
        occupied.listen()
        monkeypatch.setattr(ipc_transport, 'IPC_PORT', occupied.getsockname()[1])
        monkeypatch.setattr(main, 'send_ipc_command', lambda command: False)
        monkeypatch.setitem(sys.modules, 'tray_app', types.SimpleNamespace(TrayApp=lambda *a, **k: calls.append('constructed')))
        monkeypatch.setattr(sys, 'argv', ['main.py', '--background'])
        try:
            main.main()
        except (SystemExit, AttributeError):
            pass
    assert calls == [], 'occupied or denied dispatch must not create display resident'


def test_unauthenticated_first_binder_never_receives_bearer(monkeypatch):
    import socket
    import threading
    import ipc_transport as ipc
    token = 'a-secret-that-must-never-be-sent-over-loopback'
    monkeypatch.setattr(ipc, 'get_or_create_ipc_token', lambda: token)
    received = []
    with socket.socket() as listener:
        listener.bind(('127.0.0.1', 0))
        listener.listen()
        monkeypatch.setattr(ipc, 'IPC_PORT', listener.getsockname()[1])
        def fake_peer():
            with listener.accept()[0] as conn:
                received.append(conn.recv(2048))
                conn.sendall(b'OK\n')
        thread = threading.Thread(target=fake_peer)
        thread.start()
        assert ipc.send_ipc_command('TOGGLE') is False
        thread.join(2)
    assert received and token.encode() not in received[0]


def test_independent_config_snapshots_share_token_and_merge_changes(tmp_path, monkeypatch):
    from config_manager import ConfigManager, get_or_create_ipc_token
    monkeypatch.setenv('NIGHT_LIGHT_BY_HT_CONFIG_DIR', str(tmp_path))
    first, second = ConfigManager(), ConfigManager()
    one = get_or_create_ipc_token(first)
    two = get_or_create_ipc_token(second)
    assert one == two
    first.set('temperature_k', 2800, save_now=False)
    first.save_immediate()
    second.set('brightness', 0.8, save_now=False)
    second.save_immediate()
    fresh = ConfigManager()
    assert fresh.get('temperature_k') == 2800
    assert fresh.get('brightness') == 0.8
    assert get_or_create_ipc_token(fresh) == one


import pytest


@pytest.mark.parametrize('module,method', [('tray_app', 'toggle_nightlight'), ('ui_flyout', '_on_toggle_clicked')])
def test_restored_warmth_survives_restart(module, method, tmp_path, monkeypatch):
    import ast
    from pathlib import Path
    from types import SimpleNamespace
    from config_manager import ConfigManager
    from nightlight_engine import NightLightEngine
    monkeypatch.setenv('NIGHT_LIGHT_BY_HT_CONFIG_DIR', str(tmp_path))
    cfg = ConfigManager()
    cfg.set('temperature_k', 6500, save_now=False)
    cfg.set('last_temperature_k', 3400, save_now=False)
    cfg.save_immediate()
    engine = NightLightEngine()
    engine.temperature_k = 6500
    tree = ast.parse(Path(module + '.py').read_text(encoding='utf-8-sig'))
    function = next(n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and n.name == method)
    namespace = {'engine': engine, 'config': cfg}
    exec(compile(ast.Module(body=[function], type_ignores=[]), module, 'exec'), namespace)
    owner = SimpleNamespace(update_tray=lambda: None, update_ui_state=lambda: None, flyout=None, hud=None, on_state_change=None)
    namespace[method](owner)
    cfg.save_immediate()
    restarted = ConfigManager()
    assert engine.is_enabled is True
    assert restarted.get('temperature_k') == engine.temperature_k == 3400


@pytest.mark.parametrize('file', ['ui_flyout.py', 'display_status.py', 'hud_overlay.py', 'wpf_jumplist.cs', 'main.py', 'create_shortcuts.py'])
def test_user_facing_names_are_night_light(file):
    from pathlib import Path
    import re
    text = Path(file).read_text(encoding='utf-8-sig')
    assert not re.search(r'Night Light by HT|HT filter|HT Warmth|HASSTECH:|HT:|HT waits|Set HT warmth', text)


def test_tray_tooltip_distinguishes_app_from_windows():
    import ast
    from pathlib import Path
    from types import SimpleNamespace
    tree = ast.parse(Path('tray_app.py').read_text(encoding='utf-8-sig'))
    function = next(n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and n.name == '_get_tooltip')
    namespace = {'engine': SimpleNamespace(temperature_k=3400, is_enabled=True)}
    exec(compile(ast.Module(body=[function], type_ignores=[]), 'tray_app.py', 'exec'), namespace)
    owner = SimpleNamespace(_get_display_status=lambda: SimpleNamespace(windows_label='OFF', hass_label='ON', summary='Night Light is active'))
    text = namespace['_get_tooltip'](owner)
    assert 'Windows Night Light: OFF' in text
    assert 'Night Light: ON' in text
    assert 'HT:' not in text


def test_importing_tray_does_not_register_shell_identity():
    script = '''import ctypes
calls = []
ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID = lambda *args: calls.append(args)
import tray_app
assert not calls, calls
'''
    result = subprocess.run([sys.executable, '-c', script], capture_output=True, text=True, env=os.environ.copy())
    assert result.returncode == 0, result.stderr


def test_debounced_writer_does_not_drop_concurrent_slider_update(tmp_path, monkeypatch):
    import threading
    import time
    import config_manager as cm
    monkeypatch.setenv('NIGHT_LIGHT_BY_HT_CONFIG_DIR', str(tmp_path))
    cfg = cm.ConfigManager()
    cfg.set('temperature_k', 2900, save_now=False)
    replace = cm.os.replace
    go = threading.Event()
    def update():
        assert go.wait(2)
        cfg.set('temperature_k', 2700, save_now=False)
    worker = threading.Thread(target=update)
    worker.start()
    def delayed_replace(source, target):
        go.set()
        time.sleep(0.1)
        replace(source, target)
    monkeypatch.setattr(cm.os, 'replace', delayed_replace)
    cfg.save_immediate()
    worker.join(2)
    assert not worker.is_alive()
    cfg.save_immediate()
    assert cm.ConfigManager().get('temperature_k') == 2700


def test_first_launch_defaults_do_not_overwrite_a_concurrent_saved_config(tmp_path, monkeypatch):
    import json
    import config_manager as cm
    monkeypatch.setenv('NIGHT_LIGHT_BY_HT_CONFIG_DIR', str(tmp_path))
    original = cm.ConfigManager.save_immediate
    def other_process_won(manager):
        manager.file_path.write_text(json.dumps({'temperature_k':2800, 'ipc_token':'x'*43}))
        original(manager)
    monkeypatch.setattr(cm.ConfigManager, 'save_immediate', other_process_won)
    cfg = cm.ConfigManager()
    assert cfg.get('temperature_k') == 2800
    assert cfg.get('ipc_token') == 'x'*43


@pytest.mark.parametrize('module,cls,preset,toggle', [('tray_app','TrayApp','apply_preset','toggle_nightlight'), ('ui_flyout','ModernFlyout','_apply_preset','_on_toggle_clicked')])
def test_repeated_off_does_not_erase_last_warmth(module, cls, preset, toggle, tmp_path, monkeypatch):
    import importlib
    from types import SimpleNamespace
    from config_manager import ConfigManager
    from nightlight_engine import NightLightEngine
    monkeypatch.setenv('NIGHT_LIGHT_BY_HT_CONFIG_DIR', str(tmp_path))
    cfg = ConfigManager()
    engine = NightLightEngine()
    engine.temperature_k = 2800
    cfg.set('temperature_k',2800,save_now=False)
    mod = importlib.import_module(module)
    monkeypatch.setattr(mod,'engine',engine)
    monkeypatch.setattr(mod,'config',cfg)
    owner=SimpleNamespace(update_ui_state=lambda:None,update_tray=lambda:None,flyout=None,hud=None,on_state_change=None)
    klass=getattr(mod,cls)
    getattr(klass,preset)(owner,6500)
    getattr(klass,preset)(owner,6500)
    getattr(klass,toggle)(owner)
    cfg.save_immediate()
    assert engine.temperature_k == cfg.get('temperature_k') == 2800


@pytest.mark.parametrize('native', [True, None])
def test_safety_pause_is_not_mislabeled_as_backend_failure(native):
    from display_status import derive_display_status
    state = derive_display_status(app_enabled=True, brightness=1, windows_active=native, backend_applied=False)
    assert state.hass_label == 'PAUSED'
    assert state.hass_effective is False
