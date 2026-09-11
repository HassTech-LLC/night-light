"""Real ephemeral loopback and independent-process regression coverage."""
import os
from pathlib import Path
import socket
import subprocess
import sys
import threading
import time
import pytest
import ipc_transport as ipc


@pytest.fixture
def resident(monkeypatch):
    from tray_app import TrayApp
    monkeypatch.setattr(ipc, 'IPC_PORT', 0)
    listener = ipc.reserve_listener()
    monkeypatch.setattr(ipc, 'IPC_PORT', listener.getsockname()[1])
    token = 'isolated-test-secret-' + 'x' * 32
    monkeypatch.setattr(ipc, 'get_or_create_ipc_token', lambda: token)
    app = TrayApp.__new__(TrayApp)
    app._server_sock = listener
    app._is_running = True
    app._ipc_token = token
    app._schedule_on_main = lambda callback: callback()
    calls = []
    app.show_flyout = lambda: calls.append('SHOW')
    app.toggle_nightlight = lambda **kwargs: calls.append('TOGGLE')
    app.apply_strength = lambda value: calls.append(('STRENGTH', value))
    app.apply_preset = lambda value: calls.append(('PRESET', value))
    app.turn_windows_nightlight_off = lambda: calls.append('WINDOWS_OFF')
    app.quit_app = lambda: calls.append('QUIT')
    app._start_ipc_server()
    yield token, calls
    app._is_running = False
    listener.close()


def connect():
    return socket.create_connection(('127.0.0.1', ipc.IPC_PORT), timeout=2)


@pytest.mark.parametrize('command,expected', [('START', []), ('SHOW', ['SHOW']), ('TOGGLE', ['TOGGLE']), ('PRESET 2800', [('PRESET', 2800)]), ('STRENGTH 70', [('STRENGTH', 70)]), ('WINDOWS_OFF', ['WINDOWS_OFF'])])
def test_real_resident_command_dispatch(resident, command, expected):
    token, calls = resident
    assert ipc.send_ipc_command(command)
    assert calls == expected


@pytest.mark.parametrize('bad', [b'wrong-token TOGGLE\n', b'\xff\n', b'[]\n', b'{}\n', b'x' * 2049, b'{"hello":17}\n'])
def test_malformed_peer_does_not_kill_real_server(resident, bad):
    with connect() as conn:
        conn.sendall(bad)
        conn.shutdown(socket.SHUT_WR)
        try:
            conn.recv(2048)
        except OSError:
            pass
    assert ipc.send_ipc_command('SHOW')
    assert resident[1] == ['SHOW']


@pytest.mark.parametrize('attack', ['reflection', 'command-change', 'previous-connection'])
def test_client_proof_rejects_reflection_replay_and_command_tamper(resident, attack):
    token, calls = resident
    cn = '1' * 64
    with connect() as conn:
        ipc._send(conn, {'hello': cn})
        challenge = ipc._receive(conn)
        sn = challenge['nonce']
        proof = ipc._proof(token, 'client', cn, sn, 'SHOW')
        if attack == 'previous-connection':
            conn.close()
            conn = connect()
            ipc._send(conn, {'hello': cn})
            newer = ipc._receive(conn)
            assert newer['nonce'] != sn
        elif attack == 'reflection':
            proof = challenge['proof']
        try:
            ipc._send(conn, {'command': 'TOGGLE' if attack == 'command-change' else 'SHOW', 'proof': proof})
            conn.shutdown(socket.SHUT_WR)
            assert not conn.recv(2048)
        finally:
            conn.close()
    assert ipc.send_ipc_command('START')
    assert calls == []


def test_unknown_command_is_not_acknowledged(resident):
    assert ipc.send_ipc_command('LAUNCH SOMETHING') is False
    assert ipc.send_ipc_command('START')


def test_authenticated_quit_is_queued_without_starting_or_toggling(resident):
    assert ipc.send_ipc_command('QUIT')
    deadline=time.monotonic()+1
    while not resident[1] and time.monotonic()<deadline:time.sleep(.001)
    assert resident[1]==['QUIT']


def test_command_process_exits_without_display_import_or_cleanup(resident):
    script = '''import sys
import ipc_transport as ipc
ipc.IPC_PORT = int(sys.argv[1])
ipc.get_or_create_ipc_token = lambda: 'isolated-test-secret-' + 'x'*32
import main
sys.argv = ['main.py', '--background']
try: main.main()
except SystemExit as exc: assert exc.code == 0, exc.code
assert 'nightlight_engine' not in sys.modules
assert 'tray_app' not in sys.modules
print('authenticated client exited without display import')
'''
    result = subprocess.run([sys.executable, '-c', script, str(ipc.IPC_PORT)], capture_output=True, text=True, env=os.environ.copy(), timeout=10)
    assert result.returncode == 0, result.stderr
    assert 'without display import' in result.stdout


def test_concurrent_processes_share_one_token_and_preserve_disjoint_writes(tmp_path):
    script = '''import sys, time, hashlib
from pathlib import Path
from config_manager import ConfigManager, get_or_create_ipc_token
root=Path(sys.argv[1]); ident=sys.argv[2]
cfg=ConfigManager()
(root/('ready-'+ident)).touch()
while not (root/'go').exists(): time.sleep(0.01)
token=get_or_create_ipc_token(cfg)
cfg.set('worker-'+ident, ident, save_now=False); cfg.save_immediate()
print(hashlib.sha256(token.encode()).hexdigest())
'''
    env = dict(os.environ, NIGHT_LIGHT_BY_HT_CONFIG_DIR=str(tmp_path))
    children = [subprocess.Popen([sys.executable, '-c', script, str(tmp_path), str(i)], env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True) for i in range(6)]
    try:
        deadline = time.monotonic() + 15
        while len(list(tmp_path.glob('ready-*'))) < 6 and time.monotonic() < deadline:
            time.sleep(0.02)
        ready = sorted(path.name for path in tmp_path.glob('ready-*'))
        if len(ready) != 6:
            diagnostics = []
            for index, process in enumerate(children):
                if process.poll() is None:
                    process.kill()
                stdout, stderr = process.communicate(timeout=5)
                diagnostics.append({
                    'id': index,
                    'returncode': process.returncode,
                    'stdout': stdout,
                    'stderr': stderr,
                })
            pytest.fail(f'only {len(ready)}/6 children became ready: {ready}; children={diagnostics}')
        (tmp_path/'go').touch()
        results = [p.communicate(timeout=20) for p in children]
        assert [p.returncode for p in children] == [0] * 6, results
        assert len({stdout.strip() for stdout, stderr in results}) == 1, results
        import json
        saved = json.loads((tmp_path/'config.json').read_text())
        assert all(saved['worker-'+str(i)] == str(i) for i in range(6))
    finally:
        for p in children:
            if p.poll() is None:
                p.kill()
                p.wait()


def test_config_reader_cannot_block_cold_writer_replace(tmp_path):
    """Schedule a real Windows open reader against a real cold-start writer."""
    writer = r'''
import builtins, sys, time
from pathlib import Path
root = Path(sys.argv[1])
original_open = builtins.open
first = True
def pause_before_writer_lock(path, *args, **kwargs):
    global first
    if first and str(path).endswith('config.json.lock'):
        first = False
        (root / 'writer-paused').touch()
        deadline = time.monotonic() + 8
        while not (root / 'reader-held').exists():
            if time.monotonic() >= deadline:
                raise TimeoutError('reader never held the config file')
            time.sleep(.005)
    return original_open(path, *args, **kwargs)
builtins.open = pause_before_writer_lock
import config_manager
print('writer-ready', flush=True)
'''
    reader = r'''
import json, sys, time
from pathlib import Path
root = Path(sys.argv[1])
original_load = json.load
def hold_real_config_handle(file, *args, **kwargs):
    value = original_load(file, *args, **kwargs)
    if str(file.name).endswith('config.json'):
        (root / 'reader-held').touch()
        time.sleep(2)
    return value
json.load = hold_real_config_handle
import config_manager
print('reader-ready', flush=True)
'''
    env = dict(
        os.environ,
        NIGHT_LIGHT_BY_HT_CONFIG_DIR=str(tmp_path),
        NIGHT_LIGHT_BY_HT_DISABLE_DISPLAY_BACKEND='1',
        PYTHONDONTWRITEBYTECODE='1',
    )
    cold_writer = subprocess.Popen(
        [sys.executable, '-B', '-c', writer, str(tmp_path)],
        env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
    )
    reader_process = None
    try:
        deadline = time.monotonic() + 5
        while not (tmp_path / 'writer-paused').exists() and time.monotonic() < deadline:
            time.sleep(.005)
        assert (tmp_path / 'writer-paused').exists(), cold_writer.communicate(timeout=5)

        seeded = subprocess.run(
            [sys.executable, '-B', '-c', 'import config_manager; print("seeded")'],
            env=env, capture_output=True, text=True, timeout=10,
        )
        assert seeded.returncode == 0, (seeded.stdout, seeded.stderr)

        reader_process = subprocess.Popen(
            [sys.executable, '-B', '-c', reader, str(tmp_path)],
            env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
        )
        deadline = time.monotonic() + 5
        while not (tmp_path / 'reader-held').exists() and time.monotonic() < deadline:
            time.sleep(.005)
        assert (tmp_path / 'reader-held').exists(), reader_process.communicate(timeout=5)

        writer_output = cold_writer.communicate(timeout=12)
        reader_output = reader_process.communicate(timeout=12)
        assert cold_writer.returncode == 0, writer_output
        assert reader_process.returncode == 0, reader_output
        assert writer_output[0].strip() == 'writer-ready'
        assert reader_output[0].strip() == 'reader-ready'
    finally:
        for process in (cold_writer, reader_process):
            if process is not None and process.poll() is None:
                process.kill()
                process.wait()
