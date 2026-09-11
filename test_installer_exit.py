"""Installer exit requests must never start a display owner or create config."""
import json
import os
from pathlib import Path
import subprocess
import sys
import pytest
import ipc_transport


def test_missing_resident_request_has_no_application_imports_or_writes(tmp_path):
    target=tmp_path/'absent-config'
    env=dict(os.environ,NIGHT_LIGHT_BY_HT_CONFIG_DIR=str(target))
    code="""import sys
import main
sys.argv=['main.py','--request-exit']
try: main.main()
except SystemExit as result: assert result.code==2
else: raise AssertionError('Expected exit status')
assert 'tray_app' not in sys.modules
assert 'nightlight_engine' not in sys.modules
assert 'config_manager' not in sys.modules
"""
    result=subprocess.run([sys.executable,'-c',code],env=env,capture_output=True,text=True)
    assert result.returncode==0,result.stderr
    assert not target.exists()


def test_existing_token_is_read_without_rewriting_settings(tmp_path,monkeypatch):
    monkeypatch.setenv('NIGHT_LIGHT_BY_HT_CONFIG_DIR',str(tmp_path))
    path=tmp_path/'config.json'
    original=json.dumps({'ipc_token':'x'*43,'unrelated':'retained'}).encode()
    path.write_bytes(original)
    calls=[]
    monkeypatch.setattr(ipc_transport,'send_ipc_command',lambda command,**kwargs:calls.append((command,kwargs)) or True)
    monkeypatch.setattr(ipc_transport,'get_or_create_ipc_token',lambda:pytest.fail('Must not create a token'))
    assert ipc_transport.request_resident_exit()
    assert calls==[('QUIT',{'existing_token':'x'*43})]
    assert path.read_bytes()==original


@pytest.mark.parametrize('contents',[b'{}',b'not json',b'[]',b'{"ipc_token":"short"}'])
def test_invalid_existing_configuration_is_never_repaired(tmp_path,monkeypatch,contents):
    monkeypatch.setenv('NIGHT_LIGHT_BY_HT_CONFIG_DIR',str(tmp_path))
    path=tmp_path/'config.json';path.write_bytes(contents)
    monkeypatch.setattr(ipc_transport,'send_ipc_command',lambda *a,**k:pytest.fail('No valid existing token'))
    assert not ipc_transport.request_resident_exit()
    assert path.read_bytes()==contents


@pytest.mark.parametrize('args',[['--request-exit'],['--request-exit','--toggle']])
def test_request_exit_never_falls_through_to_resident_start(monkeypatch,args):
    import main
    monkeypatch.setattr(sys,'argv',['main.py',*args])
    monkeypatch.setattr(ipc_transport,'request_resident_exit',lambda:True)
    monkeypatch.setattr(ipc_transport,'reserve_listener',lambda:pytest.fail('Exit cannot start an owner'))
    with pytest.raises(SystemExit) as result:main.main()
    assert result.value.code==(0 if len(args)==1 else 2)
