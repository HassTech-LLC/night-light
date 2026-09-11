from pathlib import Path
import pytest
import create_shortcuts as shortcuts


@pytest.fixture
def environment(tmp_path,monkeypatch):
    user=tmp_path/'user';(user/'Desktop').mkdir(parents=True)
    appdata=user/'AppData'/'Roaming'
    (appdata/'Microsoft'/'Windows'/'Start Menu'/'Programs').mkdir(parents=True)
    pinned=appdata/'Microsoft'/'Internet Explorer'/'Quick Launch'/'User Pinned'/'TaskBar'/'Night Light.lnk'
    pinned.parent.mkdir(parents=True);pinned.write_bytes(b'synthetic shortcut')
    project=tmp_path/'source';project.mkdir()
    (project/'dist').mkdir();(project/'dist'/'NightLight.exe').write_bytes(b'stale fixture')
    (project/'assets').mkdir();(project/'assets'/'app.ico').write_bytes(b'icon fixture')
    monkeypatch.setenv('USERPROFILE',str(user));monkeypatch.setenv('APPDATA',str(appdata))
    monkeypatch.setattr(shortcuts,'__file__',str(project/'create_shortcuts.py'))
    calls=[];monkeypatch.setattr(shortcuts,'create_shortcut',lambda **kwargs:calls.append(kwargs))
    return project,calls


def test_packaged_shortcuts_target_running_install_not_dist_or_extraction(environment,tmp_path,monkeypatch):
    project,calls=environment
    executable=tmp_path/'installed'/'release-id'/'NightLight.exe'
    executable.parent.mkdir(parents=True);executable.write_bytes(b'installed fixture')
    monkeypatch.setattr(shortcuts.sys,'frozen',True,raising=False)
    monkeypatch.setattr(shortcuts.sys,'executable',str(executable))
    shortcuts.create_all_shortcuts()
    assert len(calls)==4
    for call in (calls[0],calls[2]):
        assert call['target_path']==executable
        assert call['icon_path']==executable
        assert call['working_dir']==executable.parent
        assert call['arguments']=='--show'
    assert calls[1]['shortcut_path'].name=='Night Light.lnk'
    assert calls[1]['arguments']=='--toggle'
    assert calls[2]['shortcut_path'].name=='Night Light Controls.lnk'
    assert calls[3]['shortcut_path'].name=='Night Light.lnk'
    assert calls[3]['arguments']=='--toggle'


def test_source_shortcuts_never_select_stale_dist(environment,tmp_path,monkeypatch):
    project,calls=environment
    python=tmp_path/'runtime'/'python.exe';python.parent.mkdir()
    python.write_bytes(b'python fixture')
    pythonw=python.with_name('pythonw.exe');pythonw.write_bytes(b'pythonw fixture')
    monkeypatch.setattr(shortcuts.sys,'frozen',False,raising=False)
    monkeypatch.setattr(shortcuts.sys,'executable',str(python))
    shortcuts.create_all_shortcuts()
    for call in (calls[0],calls[2]):
        assert call['target_path']==pythonw
        assert call['arguments']==f'"{project / "main.py"}" --show'
        assert call['working_dir']==project
    assert calls[1]['arguments']==f'"{project / "main.py"}" --toggle'
    assert calls[3]['arguments']==f'"{project / "main.py"}" --toggle'
