"""Exercise the compiled GUI process with redirected pipes (no display engine)."""
import json
import queue
import subprocess
import threading
from pathlib import Path

root=Path(__file__).resolve().parents[1]
base=root/'assets/premium'
p=subprocess.Popen([str(base/'NightLight.Premium.exe'),str(base),str(root/'audit/premium-qa/host-regression'),str(root/'audit/premium-qa/host-fixed.png')],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,encoding='utf-8',creationflags=0x08000000)
events=queue.Queue()
def read():
    for line in p.stdout:events.put(json.loads(line))
threading.Thread(target=read,daemon=True).start()
try:
    while True:
        event=events.get(timeout=15)
        if event.get('kind')=='failed':raise RuntimeError('WebView2 initialization failed')
        if event.get('kind')=='captured':break
    p.stdin.write('{"kind":"close"}\n');p.stdin.flush()
    p.wait(timeout=10)
    assert p.returncode==0
    print('PASS: compiled GUI pipe startup, navigation, capture and graceful exit')
finally:
    if p.poll() is None:p.kill()
