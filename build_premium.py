"""Build the desktop surface from the approved design and pinned WebView2 SDK."""
from pathlib import Path
import hashlib
import json
import shutil
import subprocess
import urllib.request
import zipfile

VERSION = '1.0.4191.47'
SDK_SHA256 = 'f492bbf547d0da329553b6727435b677579b1e9f91cc9e4a1ad029366d5f23d0'
ROOT = Path(__file__).resolve().parent

def build_premium():
    package = ROOT / 'audit/webview-sdk/package'
    archive = ROOT / 'audit/webview-sdk/sdk.zip'
    if not archive.exists():
        archive.parent.mkdir(parents=True, exist_ok=True)
        # Scheme and host are fixed to HTTPS; the archive is rejected immediately
        # below unless it matches the release-pinned SHA-256.
        urllib.request.urlretrieve(f'https://api.nuget.org/v3-flatcontainer/microsoft.web.webview2/{VERSION}/microsoft.web.webview2.{VERSION}.nupkg', archive)  # nosec B310
    if hashlib.sha256(archive.read_bytes()).hexdigest() != SDK_SHA256:
        raise RuntimeError('Pinned WebView2 SDK hash mismatch')
    with zipfile.ZipFile(archive) as sdk:
        sdk.extractall(package)
    target=ROOT/'assets/premium'
    target.mkdir(parents=True,exist_ok=True)
    allowed={'Microsoft.Web.WebView2.Core.dll','Microsoft.Web.WebView2.WinForms.dll','WebView2Loader.dll','NightLight.Premium.exe','index.html','base.css','appearance.css','appearance.js','desktop.css','desktop.js','favicon.ico','ORIGINS.json'}
    unexpected=[p.name for p in target.iterdir() if p.name not in allowed]
    if unexpected:raise RuntimeError('Unexpected premium build inputs: '+', '.join(unexpected))
    for name in ['Microsoft.Web.WebView2.Core.dll','Microsoft.Web.WebView2.WinForms.dll']:
        shutil.copy2(package/'lib/net462'/name,target/name)
    shutil.copy2(package/'runtimes/win-x64/native/WebView2Loader.dll',target/'WebView2Loader.dll')
    shutil.copy2(ROOT/'assets/app.ico',target/'favicon.ico')
    # A build must never rewrite a declared source input. Git may check the
    # committed notice out with CRLF while NuGet ships LF, so compare semantic
    # lines and fail closed if the pinned package's license text really changed.
    package_license = (package/'LICENSE.txt').read_text(encoding='utf-8-sig').splitlines()
    committed_license = (ROOT/'THIRD-PARTY-LICENSES/WebView2-LICENSE.txt').read_text(encoding='utf-8-sig').splitlines()
    if package_license != committed_license:
        raise RuntimeError('Pinned WebView2 SDK license differs from the committed notice')
    csc=Path(r'C:\Windows\Microsoft.NET\Framework64\v4.0.30319\csc.exe')
    subprocess.run([str(csc),'/nologo','/target:winexe','/platform:x64',
                    '/r:System.Windows.Forms.dll','/r:System.Drawing.dll','/r:System.Web.Extensions.dll',
                    f'/r:{target / "Microsoft.Web.WebView2.Core.dll"}',
                    f'/r:{target / "Microsoft.Web.WebView2.WinForms.dll"}',
                    f'/win32icon:{ROOT / "assets/app.ico"}',
                    f'/out:{target / "NightLight.Premium.exe"}',str(ROOT/'premium_host.cs')],check=True)
    source=(ROOT/'docs/design/night-light-premium-concept.html').read_text(encoding='utf-8')
    style=source.split('<style>',1)[1].split('</style>',1)[0]
    appearance=source.split('<div class="theme-field">',1)[1].split('<div class="scenario-field">',1)[0]
    card=source.split('<section class="flyout"',1)[1].split('</section>\n      </div>',1)[0]
    card='<section class="flyout"'+card+'</section>'
    card=card.replace('</div>\n\n        <div class="status"','<button class="window-control" id="minimize" aria-label="Minimize window" title="Minimize"><svg viewBox="0 0 16 16"><path d="M4 8h8"/></svg></button><button class="window-control" id="close-window" aria-label="Close controls, keep running" title="Close controls"><svg viewBox="0 0 16 16"><path d="m4 4 8 8M12 4l-8 8"/></svg></button></div>\n\n        <div class="status"',1)
    # The approved controls remain identical; replace only demo behavior/copy.
    card=card.replace('max="82"','max="106"').replace('max="40"','max="80"')
    card=card.replace('Color sample only','Your actual display').replace('Example schedule','Local solar schedule')
    card=card.replace('A change in Smart mode lasts 60 minutes, until 9:45 PM in this example.','A change in Smart mode lasts 60 minutes.')
    card=card.replace('Forty percent is the maximum dimming in this concept. Only the small sample is affected.','Software dimming affects the whole display; up to 80 percent dimmer.')
    card=card.replace('show the original sample. Release to restore the filtered sample.','show original display colors. Release to restore your filter.')
    start=card.index('        <details class="settings">')
    card=card[:start]+(ROOT/'premium/settings.html').read_text(encoding='utf-8')+'\n<details class="settings appearance-panel"><summary>Appearance &amp; presets</summary><div class="intro"><div class="concept-controls"><div class="theme-field">'+appearance+'</div></div></details>\n</section>'
    page='<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta http-equiv="Content-Security-Policy" content="default-src \'self\'; script-src \'self\'; style-src \'self\' \'unsafe-inline\'; img-src \'self\' data:; connect-src \'none\'; object-src \'none\'; base-uri \'none\'"><title>Night Light by HT</title><link rel="stylesheet" href="base.css"><link rel="stylesheet" href="appearance.css"><link rel="stylesheet" href="desktop.css"></head><body data-material="liquid"><main class="desktop-shell"><div class="material-stage">'+card+'</div><p id="announcer" role="status" class="sr-only"></p></main><script src="desktop.js"></script><script src="appearance.js"></script></body></html>'
    (target/'index.html').write_text(page,encoding='utf-8')
    (target/'base.css').write_text(style,encoding='utf-8')
    shutil.copy2(ROOT/'docs/design/appearance.css',target/'appearance.css')
    appjs=(ROOT/'docs/design/appearance.js').read_text(encoding='utf-8')
    appjs=appjs.replace('night-light-concept-appearance-v1','night-light-desktop-appearance-v1').replace('Saved in this browser.','Saved on this computer.').replace('Browser storage','Local storage')
    (target/'appearance.js').write_text(appjs,encoding='utf-8')
    for name in ['desktop.js','desktop.css']:
        shutil.copy2(ROOT/'premium'/name,target/name)
    manifest={'sdk':VERSION,'sdk_sha256':hashlib.sha256(archive.read_bytes()).hexdigest(),
              'compiler_sha256':hashlib.sha256(csc.read_bytes()).hexdigest(),
              'host_source_sha256':hashlib.sha256((ROOT/'premium_host.cs').read_bytes()).hexdigest(),
              'files':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in target.iterdir() if p.is_file() and p.name!='ORIGINS.json'}}
    (target/'ORIGINS.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
    return target

if __name__=='__main__':
    print(build_premium())
