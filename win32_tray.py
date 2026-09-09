"""Small Windows notification-area icon built only on ctypes.

The public ``TrayIcon`` surface intentionally mirrors the tiny subset Night Light
needs: detached operation, left/right click callbacks, mutable icon/title, and
idempotent stop.  Win32 calls live behind a backend so behavior is unit-testable
without creating a real notification icon.
"""

from __future__ import annotations

import ctypes
from ctypes import wintypes
from pathlib import Path
import tempfile
import threading
from typing import Callable, Optional


WM_DESTROY = 0x0002
WM_CLOSE = 0x0010
WM_LBUTTONUP = 0x0202
WM_RBUTTONUP = 0x0205
WM_CONTEXTMENU = 0x007B
WM_APP = 0x8000
WM_TRAY_CALLBACK = WM_APP + 1
WM_TRAY_UPDATE = WM_APP + 2

NIM_ADD = 0x00000000
NIM_MODIFY = 0x00000001
NIM_DELETE = 0x00000002
NIM_SETVERSION = 0x00000004
NIF_MESSAGE = 0x00000001
NIF_ICON = 0x00000002
NIF_TIP = 0x00000004
NOTIFYICON_VERSION_4 = 4
IMAGE_ICON = 1
LR_LOADFROMFILE = 0x0010
LR_DEFAULTSIZE = 0x0040


class TrayIcon:
    """A testable notification-area icon with Night Light's click semantics."""

    def __init__(
        self,
        name: str,
        icon,
        title: str,
        on_left_click: Optional[Callable[["TrayIcon"], None]] = None,
        on_right_click: Optional[Callable[["TrayIcon"], None]] = None,
        backend_factory=None,
    ) -> None:
        self.name = name
        self._icon = icon
        self._title = title
        self.on_left_click = on_left_click
        self.on_right_click = on_right_click
        self._backend = (backend_factory or _Win32Backend)(self)
        self._thread: Optional[threading.Thread] = None

    @property
    def icon(self):
        return self._icon

    @icon.setter
    def icon(self, value) -> None:
        self._icon = value
        if self._thread is not None:
            self._backend.update()

    @property
    def title(self) -> str:
        return self._title

    @title.setter
    def title(self, value: str) -> None:
        self._title = str(value)
        if self._thread is not None:
            self._backend.update()

    def _handle_message(self, message: int) -> None:
        if message == WM_LBUTTONUP and self.on_left_click:
            self.on_left_click(self)
        elif message in (WM_RBUTTONUP, WM_CONTEXTMENU) and self.on_right_click:
            self.on_right_click(self)

    def run_detached(self) -> None:
        if self._thread is not None and self._thread.is_alive():
            return
        self._thread = threading.Thread(
            target=self._backend.run,
            name=f"{self.name}-tray",
            daemon=True,
        )
        self._thread.start()
        ready = getattr(self._backend, "ready", None)
        if ready is not None:
            ready.wait(timeout=5)
        else:
            self._thread.join(timeout=0.05)

    def stop(self) -> None:
        self._backend.stop()
        thread = self._thread
        if thread is not None and thread is not threading.current_thread():
            thread.join(timeout=5)
        self._thread = None


if hasattr(ctypes, "WINFUNCTYPE"):
    _WNDPROC = ctypes.WINFUNCTYPE(
        ctypes.c_ssize_t,
        wintypes.HWND,
        wintypes.UINT,
        wintypes.WPARAM,
        wintypes.LPARAM,
    )
else:  # Keeps source importable for non-Windows static analysis.
    _WNDPROC = ctypes.CFUNCTYPE(
        ctypes.c_ssize_t,
        wintypes.HWND,
        wintypes.UINT,
        wintypes.WPARAM,
        wintypes.LPARAM,
    )


class _WNDCLASSW(ctypes.Structure):
    _fields_ = [
        ("style", wintypes.UINT),
        ("lpfnWndProc", _WNDPROC),
        ("cbClsExtra", ctypes.c_int),
        ("cbWndExtra", ctypes.c_int),
        ("hInstance", wintypes.HINSTANCE),
        ("hIcon", wintypes.HICON),
        ("hCursor", wintypes.HANDLE),
        ("hbrBackground", wintypes.HBRUSH),
        ("lpszMenuName", wintypes.LPCWSTR),
        ("lpszClassName", wintypes.LPCWSTR),
    ]


class _GUID(ctypes.Structure):
    _fields_ = [
        ("Data1", wintypes.DWORD),
        ("Data2", wintypes.WORD),
        ("Data3", wintypes.WORD),
        ("Data4", ctypes.c_ubyte * 8),
    ]


class _NOTIFYICONDATAW(ctypes.Structure):
    _fields_ = [
        ("cbSize", wintypes.DWORD),
        ("hWnd", wintypes.HWND),
        ("uID", wintypes.UINT),
        ("uFlags", wintypes.UINT),
        ("uCallbackMessage", wintypes.UINT),
        ("hIcon", wintypes.HICON),
        ("szTip", wintypes.WCHAR * 128),
        ("dwState", wintypes.DWORD),
        ("dwStateMask", wintypes.DWORD),
        ("szInfo", wintypes.WCHAR * 256),
        ("uVersion", wintypes.UINT),
        ("szInfoTitle", wintypes.WCHAR * 64),
        ("dwInfoFlags", wintypes.DWORD),
        ("guidItem", _GUID),
        ("hBalloonIcon", wintypes.HICON),
    ]


def _configure_win32_api(user32, shell32, kernel32) -> None:
    """Declare Win32 signatures so 64-bit handles are never truncated."""
    kernel32.GetModuleHandleW.argtypes = [wintypes.LPCWSTR]
    kernel32.GetModuleHandleW.restype = wintypes.HMODULE
    user32.RegisterClassW.argtypes = [ctypes.POINTER(_WNDCLASSW)]
    user32.RegisterClassW.restype = wintypes.WORD
    user32.CreateWindowExW.argtypes = [
        wintypes.DWORD, wintypes.LPCWSTR, wintypes.LPCWSTR, wintypes.DWORD,
        ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int,
        wintypes.HWND, wintypes.HANDLE, wintypes.HINSTANCE, wintypes.LPVOID,
    ]
    user32.CreateWindowExW.restype = wintypes.HWND
    user32.LoadImageW.argtypes = [
        wintypes.HINSTANCE, wintypes.LPCWSTR, wintypes.UINT,
        ctypes.c_int, ctypes.c_int, wintypes.UINT,
    ]
    user32.LoadImageW.restype = wintypes.HANDLE
    user32.DestroyIcon.argtypes = [wintypes.HICON]
    user32.DestroyIcon.restype = wintypes.BOOL
    user32.PostMessageW.argtypes = [wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM]
    user32.PostMessageW.restype = wintypes.BOOL
    user32.GetMessageW.argtypes = [ctypes.POINTER(wintypes.MSG), wintypes.HWND, wintypes.UINT, wintypes.UINT]
    user32.GetMessageW.restype = ctypes.c_int
    user32.TranslateMessage.argtypes = [ctypes.POINTER(wintypes.MSG)]
    user32.TranslateMessage.restype = wintypes.BOOL
    user32.DispatchMessageW.argtypes = [ctypes.POINTER(wintypes.MSG)]
    user32.DispatchMessageW.restype = ctypes.c_ssize_t
    user32.DestroyWindow.argtypes = [wintypes.HWND]
    user32.DestroyWindow.restype = wintypes.BOOL
    user32.PostQuitMessage.argtypes = [ctypes.c_int]
    user32.PostQuitMessage.restype = None
    user32.DefWindowProcW.argtypes = [wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM]
    user32.DefWindowProcW.restype = ctypes.c_ssize_t
    shell32.Shell_NotifyIconW.argtypes = [wintypes.DWORD, ctypes.POINTER(_NOTIFYICONDATAW)]
    shell32.Shell_NotifyIconW.restype = wintypes.BOOL


class _Win32Backend:
    """Win32 Shell_NotifyIcon backend; instantiated only by the real app."""

    def __init__(self, owner: TrayIcon) -> None:
        if not hasattr(ctypes, "windll"):
            raise OSError("Night Light tray icons require Windows")
        self.owner = owner
        self.ready = threading.Event()
        self._hwnd = None
        self._hicon = None
        self._icon_file: Optional[Path] = None
        self._class_name = f"NightLight.Tray.{id(self):x}"
        self._wndproc = _WNDPROC(self._window_proc)
        self._user32 = ctypes.windll.user32
        self._shell32 = ctypes.windll.shell32
        self._kernel32 = ctypes.windll.kernel32
        _configure_win32_api(self._user32, self._shell32, self._kernel32)

    def _save_and_load_icon(self):
        handle = tempfile.NamedTemporaryFile(prefix="night-light-tray-", suffix=".ico", delete=False)
        handle.close()
        path = Path(handle.name)
        self.owner.icon.save(path, format="ICO")
        hicon = self._user32.LoadImageW(None, str(path), IMAGE_ICON, 0, 0, LR_LOADFROMFILE | LR_DEFAULTSIZE)
        if not hicon:
            path.unlink(missing_ok=True)
            raise ctypes.WinError()
        old_file = self._icon_file
        self._icon_file = path
        if old_file:
            old_file.unlink(missing_ok=True)
        return hicon

    def _notify_data(self) -> _NOTIFYICONDATAW:
        data = _NOTIFYICONDATAW()
        data.cbSize = ctypes.sizeof(data)
        data.hWnd = self._hwnd
        data.uID = 1
        data.uFlags = NIF_MESSAGE | NIF_ICON | NIF_TIP
        data.uCallbackMessage = WM_TRAY_CALLBACK
        data.hIcon = self._hicon
        data.szTip = self.owner.title[:127]
        return data

    def run(self) -> None:
        instance = self._kernel32.GetModuleHandleW(None)
        window_class = _WNDCLASSW()
        window_class.lpfnWndProc = self._wndproc
        window_class.hInstance = instance
        window_class.lpszClassName = self._class_name
        if not self._user32.RegisterClassW(ctypes.byref(window_class)):
            self.ready.set()
            raise ctypes.WinError()
        self._hwnd = self._user32.CreateWindowExW(
            0, self._class_name, self.owner.name, 0, 0, 0, 0, 0,
            None, None, instance, None,
        )
        if not self._hwnd:
            self.ready.set()
            raise ctypes.WinError()
        self._hicon = self._save_and_load_icon()
        data = self._notify_data()
        if not self._shell32.Shell_NotifyIconW(NIM_ADD, ctypes.byref(data)):
            self.ready.set()
            raise ctypes.WinError()
        data.uVersion = NOTIFYICON_VERSION_4
        self._shell32.Shell_NotifyIconW(NIM_SETVERSION, ctypes.byref(data))
        self.ready.set()

        message = wintypes.MSG()
        while self._user32.GetMessageW(ctypes.byref(message), None, 0, 0) > 0:
            self._user32.TranslateMessage(ctypes.byref(message))
            self._user32.DispatchMessageW(ctypes.byref(message))

    def update(self) -> None:
        if self._hwnd:
            self._user32.PostMessageW(self._hwnd, WM_TRAY_UPDATE, 0, 0)

    def _apply_update(self) -> None:
        old_icon = self._hicon
        self._hicon = self._save_and_load_icon()
        data = self._notify_data()
        if not self._shell32.Shell_NotifyIconW(NIM_MODIFY, ctypes.byref(data)):
            raise ctypes.WinError()
        if old_icon:
            self._user32.DestroyIcon(old_icon)

    def stop(self) -> None:
        if self._hwnd:
            self._user32.PostMessageW(self._hwnd, WM_CLOSE, 0, 0)

    def _window_proc(self, hwnd, message, wparam, lparam):
        if message == WM_TRAY_CALLBACK:
            self.owner._handle_message(int(lparam) & 0xFFFF)
            return 0
        if message == WM_TRAY_UPDATE:
            self._apply_update()
            return 0
        if message == WM_CLOSE:
            self._shell32.Shell_NotifyIconW(NIM_DELETE, ctypes.byref(self._notify_data()))
            self._user32.DestroyWindow(hwnd)
            return 0
        if message == WM_DESTROY:
            if self._hicon:
                self._user32.DestroyIcon(self._hicon)
                self._hicon = None
            if self._icon_file:
                self._icon_file.unlink(missing_ok=True)
                self._icon_file = None
            self._user32.PostQuitMessage(0)
            return 0
        return self._user32.DefWindowProcW(hwnd, message, wparam, lparam)
