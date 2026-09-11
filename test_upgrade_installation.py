"""Real PowerShell upgrade operations against isolated synthetic payloads only."""
import ctypes
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import pytest

SCRIPT=Path(__file__).parent/'installer/upgrade.ps1'


def receipt(root):
    return dict(schema=1,product_id='com.hasstech.night-light',files=[
        dict(path=p.name,size=p.stat().st_size,sha256=hashlib.sha256(p.read_bytes()).hexdigest())
        for p in sorted(root.iterdir()) if p.is_file()])


@pytest.fixture
def upgrade(tmp_path):
    local=tmp_path/'Local'; roaming=tmp_path/'Roaming'
    local.mkdir()
    (local/'.night-light-installer-test-root').write_text('isolated synthetic fixture')
    installed=local/'Programs'/'Night Light'
    incoming=tmp_path/'incoming'; incoming.mkdir()
    (incoming/'NightLight.exe').write_bytes(b'synthetic NEW executable never run')
    (incoming/'LICENSE').write_bytes(b'new license')
    ownership=incoming/'OWNED-FILES.json'
    ownership.write_text(json.dumps(receipt(incoming)))
    identity=hashlib.sha256(ownership.read_bytes()).hexdigest()
    scripts=tmp_path/'scripts'; scripts.mkdir()
    shutil.copyfile(SCRIPT,scripts/'upgrade.ps1')
    old=installed/('a'*40); old.mkdir(parents=True)
    (old/'NightLight.exe').write_bytes(b'synthetic OLD executable never run')
    (old/'LICENSE').write_bytes(b'old license')
    catalog=receipt(old); catalog['directory']=old.name
    (scripts/'legacy-installations.json').write_text(json.dumps(dict(schema=1,installations=[catalog])))
    config=roaming/'NightLightWidget'/'config.json'; config.parent.mkdir(parents=True)
    config.write_bytes(b'private synthetic preferences remain unchanged')
    def run(verify=False,point=None,crash=False):
        command=['powershell','-NoProfile','-NonInteractive','-File',str(scripts/'upgrade.ps1'),
                 '-IncomingRoot',str(incoming),'-ReceiptSha256',identity]
        if verify:command.append('-VerifyOnly')
        if point:command += ['-TestFailurePoint',point]
        if crash:command.append('-TestCrash')
        result=subprocess.run(command,env=dict(os.environ,LOCALAPPDATA=str(local),APPDATA=str(roaming),NIGHT_LIGHT_INSTALL_TEST_MODE='1'),capture_output=True,text=True,timeout=30)
        assert config.read_bytes()==b'private synthetic preferences remain unchanged'
        return result
    return old,incoming,installed,run


def test_preflight_is_read_only(upgrade):
    old,incoming,installed,run=upgrade
    result=run(True)
    assert result.returncode==0,result.stderr
    assert (old/'NightLight.exe').exists()
    assert not (installed/'app').exists()


def test_upgrade_removes_previous_app_and_preserves_unknown_files(upgrade):
    old,incoming,installed,run=upgrade
    (old/'user-note.txt').write_text('keep me')
    result=run()
    assert result.returncode==0,result.stderr
    assert not (old/'NightLight.exe').exists()
    assert not (old/'LICENSE').exists()
    assert (old/'user-note.txt').read_text()=='keep me'
    assert (installed/'app'/'NightLight.exe').read_bytes()==(incoming/'NightLight.exe').read_bytes()
    assert json.loads((installed/'INSTALLATION.json').read_text())['pending_cleanup']==[]


def test_fresh_install_has_one_app(upgrade):
    old,incoming,installed,run=upgrade
    shutil.rmtree(old)
    result=run()
    assert result.returncode==0,result.stderr
    assert list(installed.rglob('NightLight.exe'))==[installed/'app'/'NightLight.exe']


def test_next_upgrade_recognizes_stable_install_and_removes_previous_payload(upgrade):
    old,incoming,installed,run=upgrade
    assert run().returncode==0
    result=run()
    assert result.returncode==0,result.stderr
    assert list(installed.rglob('NightLight.exe'))==[installed/'app'/'NightLight.exe']
    assert not list(installed.glob('.previous-*'))


@pytest.mark.parametrize('point',['prepared','previous_reserved','replacement_promoted','integration_updated'])
def test_precommit_failure_restores_single_coherent_install(upgrade,point):
    old,incoming,installed,run=upgrade
    assert run().returncode==0
    prior=(installed/'app'/'NightLight.exe').read_bytes()
    result=run(point=point)
    assert result.returncode==2,result.stderr
    assert (installed/'app'/'NightLight.exe').read_bytes()==prior
    assert list(installed.rglob('NightLight.exe'))==[installed/'app'/'NightLight.exe']
    assert not (installed/'INSTALL-TRANSACTION.json').exists()
    assert not list(installed.glob('.failed-*'))


@pytest.mark.parametrize('point',['prepared','previous_reserved','replacement_promoted','integration_updated'])
def test_process_exit_is_recovered_idempotently_on_next_setup(upgrade,point):
    old,incoming,installed,run=upgrade
    assert run().returncode==0
    crashed=run(point=point,crash=True)
    assert crashed.returncode==91
    recovered=run()
    assert recovered.returncode==0,recovered.stderr
    assert list(installed.rglob('NightLight.exe'))==[installed/'app'/'NightLight.exe']
    assert not (installed/'INSTALL-TRANSACTION.json').exists()
    assert not list(installed.glob('.previous-*'))


def test_owned_pinned_shortcut_becomes_instant_toggle(upgrade):
    old,incoming,installed,run=upgrade
    appdata=installed.parents[2]/'Roaming'
    pinned=appdata/'Microsoft'/'Internet Explorer'/'Quick Launch'/'User Pinned'/'TaskBar'/'Night Light.lnk'
    pinned.parent.mkdir(parents=True)
    env=dict(os.environ,TEST_SHORTCUT=str(pinned),TEST_TARGET=str(old/'NightLight.exe'))
    command="$w=New-Object -ComObject WScript.Shell; $s=$w.CreateShortcut($env:TEST_SHORTCUT); $s.TargetPath=$env:TEST_TARGET; $s.Arguments='--show'; $s.Save()"
    assert subprocess.run(['powershell','-NoProfile','-Command',command],env=env).returncode==0
    result=run();assert result.returncode==0,result.stderr
    inspect="$w=New-Object -ComObject WScript.Shell; $s=$w.CreateShortcut($env:TEST_SHORTCUT); $s.TargetPath; $s.Arguments"
    output=subprocess.run(['powershell','-NoProfile','-Command',inspect],env=env,capture_output=True,text=True,check=True).stdout.splitlines()
    assert Path(output[0])==installed/'app'/'NightLight.exe'
    assert output[1]=='--toggle'


def test_fresh_start_menu_has_pin_toggle_and_separate_controls(upgrade):
    old,incoming,installed,run=upgrade
    assert run().returncode==0
    start=installed.parents[2]/'Roaming'/'Microsoft'/'Windows'/'Start Menu'/'Programs'
    env=dict(os.environ,TOGGLE_LINK=str(start/'Night Light.lnk'),CONTROLS_LINK=str(start/'Night Light Controls.lnk'))
    inspect="$w=New-Object -ComObject WScript.Shell; $w.CreateShortcut($env:TOGGLE_LINK).Arguments; $w.CreateShortcut($env:CONTROLS_LINK).Arguments"
    output=subprocess.run(['powershell','-NoProfile','-Command',inspect],env=env,capture_output=True,text=True,check=True).stdout.splitlines()
    assert output==['--toggle','--show']


@pytest.mark.parametrize('damage',['old','incoming','receipt','unknown'])
def test_changed_or_unknown_installation_stops_before_replacement(upgrade,damage):
    old,incoming,installed,run=upgrade
    if damage=='old':(old/'LICENSE').write_text('modified user file')
    elif damage=='incoming':(incoming/'NightLight.exe').write_bytes(b'damaged')
    elif damage=='receipt':(incoming/'OWNED-FILES.json').write_text('{}')
    else:
        other=installed/'unrecognized';other.mkdir()
        (other/'NightLight.exe').write_bytes(b'unknown app')
    result=run()
    assert result.returncode==2,result.stdout
    assert (old/'NightLight.exe').exists()
    assert not (installed/'app').exists()


@pytest.mark.parametrize('release_early',[False,True])
def test_file_lock_retries_then_succeeds_or_safely_stops(upgrade,release_early):
    import threading
    from ctypes import wintypes
    old,incoming,installed,run=upgrade
    kernel=ctypes.WinDLL('kernel32',use_last_error=True)
    kernel.CreateFileW.argtypes=[wintypes.LPCWSTR,wintypes.DWORD,wintypes.DWORD,ctypes.c_void_p,wintypes.DWORD,wintypes.DWORD,wintypes.HANDLE]
    kernel.CreateFileW.restype=wintypes.HANDLE
    kernel.CloseHandle.argtypes=[wintypes.HANDLE]
    handle=kernel.CreateFileW(str(old/'LICENSE'),0x80000000,1,None,3,0,None)
    assert handle!=ctypes.c_void_p(-1).value
    timer=threading.Timer(1.5,lambda:kernel.CloseHandle(handle)) if release_early else None
    if timer:timer.start()
    try:result=run()
    finally:
        if timer:timer.join()
        else:kernel.CloseHandle(handle)
    if release_early:
        assert result.returncode==0,result.stderr
        assert (installed/'app'/'NightLight.exe').exists() and not (old/'NightLight.exe').exists()
    else:
        assert result.returncode==2
        assert (old/'NightLight.exe').exists() and not (installed/'app').exists()
