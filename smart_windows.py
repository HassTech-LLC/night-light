"""Minimal Windows idle observation and registered emergency reset shortcut."""
import ctypes
import threading
from ctypes import wintypes


class LASTINPUTINFO(ctypes.Structure):
    _fields_=[('cbSize',wintypes.UINT),('dwTime',wintypes.DWORD)]


def idle_seconds():
    info=LASTINPUTINFO();info.cbSize=ctypes.sizeof(info)
    if not ctypes.windll.user32.GetLastInputInfo(ctypes.byref(info)):
        return None
    ctypes.windll.kernel32.GetTickCount.restype=wintypes.DWORD
    return ((ctypes.windll.kernel32.GetTickCount()-info.dwTime)&0xffffffff)/1000


def high_contrast_active():
    class HIGHCONTRAST(ctypes.Structure):
        _fields_=[('cbSize',wintypes.UINT),('dwFlags',wintypes.DWORD),('scheme',wintypes.LPWSTR)]
    value=HIGHCONTRAST();value.cbSize=ctypes.sizeof(value)
    if not ctypes.windll.user32.SystemParametersInfoW(0x0042,value.cbSize,ctypes.byref(value),0):return False
    return bool(value.dwFlags&1)


class EmergencyHotkey:
    """Own the hotkey message loop so Tk cannot consume thread messages."""
    def __init__(self,callback):
        self.callback=callback
        self.active=False;self.thread_id=None
        self.fired=threading.Event();self.ready=threading.Event()
        self.thread=threading.Thread(target=self._listen,daemon=True)
        self.thread.start();self.ready.wait(1)

    def _listen(self):
        self.thread_id=ctypes.windll.kernel32.GetCurrentThreadId()
        # MOD_NOREPEAT|MOD_ALT|MOD_CONTROL|MOD_SHIFT + N. Ctrl+Shift+N alone is taken by
        # Explorer (New folder), Chrome/Edge (InPrivate) and VS Code (New window);
        # a global hotkey would silently steal it from every app while we run.
        self.active=bool(ctypes.windll.user32.RegisterHotKey(None,0x484e,0x4000|1|2|4,ord('N')))
        self.ready.set()
        if not self.active:return
        message=wintypes.MSG()
        try:
            while ctypes.windll.user32.GetMessageW(ctypes.byref(message),None,0,0)>0:
                if message.message==0x0312 and message.wParam==0x484e:self.fired.set()
        finally:
            ctypes.windll.user32.UnregisterHotKey(None,0x484e)
            self.active=False

    def poll(self):
        if self.fired.is_set():
            self.fired.clear();self.callback()

    def close(self):
        if self.active:
            ctypes.windll.user32.PostThreadMessageW(self.thread_id,0x0012,0,0)
            self.thread.join(timeout=1)
