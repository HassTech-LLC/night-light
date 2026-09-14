from pathlib import Path
import pytest
from build_installer import payload_members,verify_toolchain


def test_release_payload_paths_keep_their_relative_destination():
    assert str(payload_members(['Night Light/THIRD-PARTY-LICENSES/license.txt'])[0][1])=='THIRD-PARTY-LICENSES/license.txt'


@pytest.mark.parametrize('name',['elsewhere/a.exe','Night Light/../a.exe','Night Light/C:/a.exe',
    'Night Light/$injection.exe','Night Light/a\\b.exe','Night Light/con.txt','Night Light/a.','Night Light/a\nb'])
def test_unsafe_payload_paths_are_rejected(name):
    with pytest.raises(ValueError):payload_members([name])


def test_windows_case_aliases_are_rejected():
    with pytest.raises(ValueError):payload_members(['Night Light/App.exe','Night Light/app.exe'])


def test_unpinned_compiler_tree_is_rejected(tmp_path):
    (tmp_path/'makensis.exe').write_bytes(b'not a compiler')
    with pytest.raises(ValueError):verify_toolchain(tmp_path)


def test_private_setup_uses_verified_replacement_and_never_recursively_deletes():
    script=(Path(__file__).parent/'installer/night-light.nsi').read_text()
    assert 'RequestExecutionLevel user' in script
    assert 'SetCompressor zlib' in script
    assert 'upgrade.ps1' in script and 'legacy-installations.json' in script
    assert '$PLUGINSDIR\\incoming' in script
    assert 'RMDir /r' not in script
    assert 'Delete "$INSTDIR\\Uninstall.exe"' in script
    assert 'ExecWait' not in script and 'MUI_FINISHPAGE_RUN' not in script
    assert 'remove-owned.ps1' in script and 'OWNERSHIP_SHA256' in script


def test_private_setup_keeps_unattended_install_available():
    script=(Path(__file__).parent/'installer/night-light.nsi').read_text()
    # Standard /S must keep working for scripted deployments; only a SilentInstall
    # override or a MessageBox without /SD in the install path would break it.
    import re
    assert not re.search(r'^\s*SilentInstall',script,re.M)
    install=script[script.index('Section "Install"'):script.index('Section "Uninstall"')]
    assert all('/SD' in line for line in install.splitlines() if 'MessageBox' in line)


def test_private_setup_registers_installed_apps_metadata():
    from build_installer import project_version
    script=(Path(__file__).parent/'installer/night-light.nsi').read_text()
    for value in ('"DisplayVersion" "${APP_VERSION}"','"Publisher" "HassTech"','"DisplayIcon"','"NoModify" 1','"NoRepair" 1'):
        assert value in script
    import re
    assert re.fullmatch(r'\d+\.\d+\.\d+',project_version())
