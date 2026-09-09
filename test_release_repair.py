"""Maintained regressions for independent release findings; conftest isolates native state."""
import json
from pathlib import Path
import pytest
from config_manager import ConfigManager, get_or_create_ipc_token
from test_release_security import resident
import ipc_transport as ipc


@pytest.mark.parametrize('name', ['README.md', 'docs/PRIVACY.md'])
def test_public_docs_use_night_light(name):
    text = (Path(__file__).parent / name).read_text(encoding='utf-8')
    assert 'Night Light by HT' not in text
    assert 'Night Light' in text



@pytest.mark.parametrize('command', ['PRESETJUNK 2800', 'STRENGTHJUNK 70', 'PRESET', 'STRENGTH', 'PRESET 2800 extra', 'STRENGTH 70 extra'])
def test_exact_command_verb_and_arity(resident, command):
    assert ipc.send_ipc_command(command) is False
    assert resident[1] == []
    assert ipc.send_ipc_command('START')



@pytest.mark.parametrize('tray_fails', [False, True])
def test_cleanup_failure_reports_and_releases_other_resources(monkeypatch, capsys, tray_fails):
    import tray_app
    from types import SimpleNamespace
    calls = []
    def save():
        raise PermissionError('injected save failure')
    def stop():
        calls.append('tray')
        if tray_fails:
            raise RuntimeError('injected tray failure')
    app = tray_app.TrayApp.__new__(tray_app.TrayApp)
    app.tray_icon = SimpleNamespace(stop=stop)
    app._server_sock = SimpleNamespace(close=lambda: calls.append('socket'))
    monkeypatch.setattr(tray_app.config, 'save_immediate', save)
    app.cleanup()
    assert calls == ['tray', 'socket']
    assert 'injected save failure' in capsys.readouterr().out



@pytest.mark.parametrize('raw', [b'{"enabled":', b'{oops', b'[]', b'null', b'42', b'"text"', b'\xff'])
def test_corrupt_config_quarantined_and_credentials_recover(tmp_path, monkeypatch, capsys, raw):
    monkeypatch.setenv('NIGHT_LIGHT_BY_HT_CONFIG_DIR', str(tmp_path))
    path = tmp_path / 'config.json'
    path.write_bytes(raw)
    manager = ConfigManager()
    token = get_or_create_ipc_token(manager)
    assert json.loads(path.read_text())['ipc_token'] == token
    assert any(p.read_bytes() == raw for p in tmp_path.glob('config.json.corrupt-*'))
    assert 'quarantin' in capsys.readouterr().out.lower()
    assert get_or_create_ipc_token(ConfigManager()) == token


def test_recovery_rechecks_disk_preserving_concurrent_valid_data(tmp_path, monkeypatch):
    monkeypatch.setenv('NIGHT_LIGHT_BY_HT_CONFIG_DIR', str(tmp_path))
    path = tmp_path / 'config.json'
    path.write_bytes(b'{bad')
    stale = ConfigManager()
    token = 'stable-token-' + 'a' * 40
    path.write_text(json.dumps({'ipc_token': token, 'brightness': .42, 'other': 7}))
    assert get_or_create_ipc_token(stale) == token
    assert json.loads(path.read_text())['brightness'] == .42
    assert json.loads(path.read_text())['other'] == 7
