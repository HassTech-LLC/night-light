"""Exercise the actual PowerShell remover only against this test's temp root."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import pytest

SCRIPT=Path(__file__).parent/'installer/remove-owned.ps1'


@pytest.fixture
def installed(tmp_path):
    (tmp_path/'.night-light-installer-test-root').write_text('isolated synthetic fixture')
    root=tmp_path/'Programs'/'Night Light'/'app';root.mkdir(parents=True)
    (root/'NightLight.exe').write_bytes(b'synthetic never executed app')
    (root/'LICENSE').write_bytes(b'test license')
    (root/'unknown.txt').write_bytes(b'user file')
    rows=[dict(path=name,sha256=hashlib.sha256((root/name).read_bytes()).hexdigest(),size=(root/name).stat().st_size)
          for name in ('NightLight.exe','LICENSE')]
    receipt=root/'OWNED-FILES.json'
    receipt.write_text(json.dumps(dict(schema=1,product_id='com.hasstech.night-light',files=rows)))
    digest=hashlib.sha256(receipt.read_bytes()).hexdigest()
    def run(verify=False,identity=digest):
        command=['powershell','-NoProfile','-NonInteractive','-File',str(SCRIPT),'-ReceiptSha256',identity]
        if verify:command.append('-VerifyOnly')
        return subprocess.run(command,env=dict(os.environ,LOCALAPPDATA=str(tmp_path),APPDATA=str(tmp_path/'Roaming'),
            NIGHT_LIGHT_INSTALL_TEST_MODE='1',NIGHT_LIGHT_INSTALL_TEST_DESKTOP=str(tmp_path/'Desktop'),
            NIGHT_LIGHT_INSTALL_TEST_STARTUP_FILE=str(tmp_path/'startup-value.txt')),capture_output=True,text=True,timeout=20)
    return root,run


def test_verify_only_never_deletes(installed):
    root,run=installed
    result=run(True)
    assert result.returncode==0,result.stderr
    assert (root/'NightLight.exe').exists() and (root/'OWNED-FILES.json').exists()


def test_remove_deletes_only_pinned_payload_and_receipt(installed):
    root,run=installed
    result=run()
    assert result.returncode==0,result.stderr
    assert not (root/'NightLight.exe').exists() and not (root/'LICENSE').exists()
    assert not (root/'OWNED-FILES.json').exists()
    assert (root/'unknown.txt').read_bytes()==b'user file'


def test_changed_file_blocks_all_removal(installed):
    root,run=installed
    (root/'LICENSE').write_bytes(b'user changed this file')
    result=run()
    assert result.returncode==2
    assert (root/'NightLight.exe').exists() and (root/'OWNED-FILES.json').exists()


def test_changed_receipt_cannot_authorize_extra_deletion(installed):
    root,run=installed
    receipt=root/'OWNED-FILES.json';receipt.write_bytes(receipt.read_bytes()+b' ')
    assert run().returncode==2
    assert (root/'NightLight.exe').exists() and (root/'unknown.txt').exists()


def test_missing_owned_file_allows_safe_removal_resume(installed):
    root,run=installed
    (root/'LICENSE').unlink()
    result=run()
    assert result.returncode==0,result.stderr
    assert not (root/'NightLight.exe').exists() and (root/'unknown.txt').exists()


def test_locked_file_blocks_deletion_of_earlier_verified_files(installed):
    import ctypes
    from ctypes import wintypes
    root,run=installed
    kernel=ctypes.WinDLL('kernel32',use_last_error=True)
    kernel.CreateFileW.argtypes=[wintypes.LPCWSTR,wintypes.DWORD,wintypes.DWORD,ctypes.c_void_p,wintypes.DWORD,wintypes.DWORD,wintypes.HANDLE]
    kernel.CreateFileW.restype=wintypes.HANDLE
    kernel.CloseHandle.argtypes=[wintypes.HANDLE]
    handle=kernel.CreateFileW(str(root/'LICENSE'),0x80000000,0,None,3,0,None)
    assert handle!=ctypes.c_void_p(-1).value
    try:assert run().returncode==2
    finally:kernel.CloseHandle(handle)
    assert (root/'NightLight.exe').exists() and (root/'OWNED-FILES.json').exists()


@pytest.mark.parametrize('owned',[True,False])
def test_only_matching_start_shortcut_is_removed(installed,owned):
    root,run=installed
    local=root.parents[2]
    shortcut=local/'Roaming'/'Microsoft'/'Windows'/'Start Menu'/'Programs'/'Night Light.lnk'
    shortcut.parent.mkdir(parents=True)
    target=root/'NightLight.exe' if owned else root/'other.exe'
    # Temp fixture paths are passed as data, never interpolated into commands.
    env=dict(os.environ,TEST_SHORTCUT=str(shortcut),TEST_TARGET=str(target))
    command="$w=New-Object -ComObject WScript.Shell; $s=$w.CreateShortcut($env:TEST_SHORTCUT); $s.TargetPath=$env:TEST_TARGET; $s.Arguments='--show'; $s.Save()"
    subprocess.run(['powershell','-NoProfile','-NonInteractive','-Command',command],env=env,check=True,capture_output=True)
    result=run()
    assert result.returncode==0,result.stderr
    assert shortcut.exists() is (not owned)


def test_all_owned_shortcuts_and_startup_are_removed_but_foreign_links_remain(installed):
    root,run=installed
    local=root.parents[2];roaming=local/'Roaming';desktop=local/'Desktop'
    folders=[desktop,roaming/'Microsoft'/'Windows'/'Start Menu'/'Programs',
             roaming/'Microsoft'/'Internet Explorer'/'Quick Launch'/'User Pinned'/'TaskBar']
    owned=[]
    for index,folder in enumerate(folders):
        folder.mkdir(parents=True,exist_ok=True)
        shortcut=folder/('Night Light by HT.lnk' if index==2 else 'Night Light.lnk')
        env=dict(os.environ,TEST_SHORTCUT=str(shortcut),TEST_TARGET=str(root/'NightLight.exe'),TEST_ARGS='--toggle' if index==2 else '--show')
        command="$w=New-Object -ComObject WScript.Shell; $s=$w.CreateShortcut($env:TEST_SHORTCUT); $s.TargetPath=$env:TEST_TARGET; $s.Arguments=$env:TEST_ARGS; $s.Save()"
        subprocess.run(['powershell','-NoProfile','-NonInteractive','-Command',command],env=env,check=True,capture_output=True)
        owned.append(shortcut)
    foreign=desktop/'Night Light by HT.lnk'
    env=dict(os.environ,TEST_SHORTCUT=str(foreign),TEST_TARGET=str(root/'other.exe'))
    command="$w=New-Object -ComObject WScript.Shell; $s=$w.CreateShortcut($env:TEST_SHORTCUT); $s.TargetPath=$env:TEST_TARGET; $s.Arguments='--show'; $s.Save()"
    subprocess.run(['powershell','-NoProfile','-NonInteractive','-Command',command],env=env,check=True,capture_output=True)
    startup=local/'startup-value.txt';startup.write_text(f'"{root / "NightLight.exe"}" --background')
    result=run();assert result.returncode==0,result.stderr
    assert not any(path.exists() for path in owned)
    assert foreign.exists() and not startup.exists()
