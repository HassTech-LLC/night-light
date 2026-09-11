"""Compile a private setup candidate from a verified, source-bound release ZIP."""
import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import subprocess
import zipfile
from release import verify_release,source_manifest

ROOT=Path(__file__).resolve().parent


def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def verify_toolchain(root):
    lock=json.loads((ROOT/'installer/toolchain.json').read_text())
    rows=[(p.relative_to(root).as_posix(),digest(p)) for p in sorted(root.rglob('*')) if p.is_file()]
    tree=hashlib.sha256(json.dumps(rows,separators=(',',':')).encode()).hexdigest()
    if tree!=lock['tree_sha256'] or digest(root/'makensis.exe')!=lock['compiler_sha256']:
        raise ValueError('NSIS toolchain differs from the pinned package.')
    return lock


def payload_members(names):
    seen=set();result=[]
    for name in names:
        path=PurePosixPath(name)
        if (path.parts[:1]!=('Night Light',) or len(path.parts)<2 or '..' in path.parts
                or any(char in name for char in ('\\',':','$','"','\n','\r'))):
            raise ValueError('Unsafe installer archive path.')
        relative=PurePosixPath(*path.parts[1:])
        reserved={'con','prn','aux','nul'}|{f'{prefix}{n}' for prefix in ('com','lpt') for n in range(1,10)}
        if any(part!=part.rstrip(' .') or part.split('.')[0].casefold() in reserved or
               any(ord(c)<32 for c in part) for part in relative.parts):
            raise ValueError('Unsupported Windows payload path.')
        key=str(relative).casefold()
        if key in seen:raise ValueError('Duplicate installer archive path.')
        seen.add(key);result.append((name,relative))
    return result


def build_installer(archive,toolchain,output_dir):
    archive=archive.resolve();toolchain=toolchain.resolve();output_dir=output_dir.resolve()
    lock=verify_toolchain(toolchain)
    result=verify_release(archive)
    if not result['valid']:raise ValueError('Release archive failed verification: '+str(result['errors']))
    if output_dir.exists():raise ValueError('Use a new output directory; existing artifacts are not overwritten.')
    for path in (output_dir,archive,toolchain):
        if any(c in str(path) for c in ('$','"','\n','\r')):raise ValueError('Unsupported compiler path characters.')
    with zipfile.ZipFile(archive) as bundle:
        members=payload_members(bundle.namelist())
        if sum(i.file_size for i in bundle.infolist())>512*1024*1024:raise ValueError('Payload exceeds setup size limit.')
        recorded=json.loads(bundle.read('Night Light/SOURCE-MANIFEST.json'))
        if recorded['files']!=source_manifest(ROOT)['files']:
            raise ValueError('Archive predates current source; rebuild before compiling setup.')
        output_dir.mkdir(parents=True)
        stage=output_dir/'payload';stage.mkdir()
        directives=['!macro PayloadFiles']
        for name,relative in members:
            target=stage.joinpath(*relative.parts);target.parent.mkdir(parents=True,exist_ok=True)
            target.write_bytes(bundle.read(name))
            destination='\\'.join(relative.parts[:-1])
            directives += ['SetOutPath "$PLUGINSDIR\\incoming'+('\\'+destination if destination else '')+'"',
                           'File "'+str(target)+'"','IfErrors install_failed']
        notice=stage/'NSIS-COPYING.txt';notice.write_bytes((toolchain/'COPYING').read_bytes())
        owned=dict(schema=1,product_id='com.hasstech.night-light',files=[
            dict(path=p.relative_to(stage).as_posix(),sha256=digest(p),size=p.stat().st_size)
            for p in sorted(stage.rglob('*')) if p.is_file()])
        ownership=stage/'OWNED-FILES.json'
        ownership.write_text(json.dumps(owned,sort_keys=True,indent=2)+'\n',encoding='utf-8')
        directives+=['SetOutPath "$PLUGINSDIR\\incoming"','File "'+str(notice)+'"','IfErrors install_failed',
                     'File "'+str(ownership)+'"','IfErrors install_failed','!macroend',
                     '!define OWNERSHIP_SHA256 "'+digest(ownership)+'"']
        include=output_dir/'payload.nsh';include.write_text('\n'.join(directives)+'\n',encoding='utf-8')
    output=output_dir/'NightLightSetup-private.exe'
    subprocess.run([str(toolchain/'makensis.exe'),'/INPUTCHARSET','UTF8','/WX','/V2',f'/DSETUP_OUTPUT={output}',
                    f'/DPAYLOAD_INCLUDE={include}',str(ROOT/'installer/night-light.nsi')],check=True)
    receipt=dict(private_candidate=True,installed=False,published=False,installer_sha256=digest(output),
                 source_archive_sha256=digest(archive),compiler=lock,
                 script_sha256=digest(ROOT/'installer/night-light.nsi'))
    (output_dir/'SETUP-BUILD.json').write_text(json.dumps(receipt,indent=2)+'\n',encoding='utf-8')
    return receipt


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--archive',type=Path,required=True)
    parser.add_argument('--toolchain',type=Path,required=True)
    parser.add_argument('--output-dir',type=Path,required=True)
    args=parser.parse_args()
    print(json.dumps(build_installer(args.archive,args.toolchain,args.output_dir),indent=2))
