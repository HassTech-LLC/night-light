"""
Configuration and Windows integration manager for Night Light by HT.
Handles JSON persistence with debouncing to prevent disk stutter during slider dragging.
"""

import json
import os
from pathlib import Path
import secrets
import sys
import tempfile
import threading
import time
import msvcrt
from contextlib import contextmanager
import winreg
from typing import Any, Dict, Optional


APP_NAME = "NightLightWidget"
REG_RUN_PATH = r"Software\Microsoft\Windows\CurrentVersion\Run"


def get_config_dir() -> Path:
    """Returns the persistent configuration directory in %APPDATA%."""
    override = os.environ.get("NIGHT_LIGHT_BY_HT_CONFIG_DIR")
    if override:
        p = Path(override)
        p.mkdir(parents=True, exist_ok=True)
        return p

    appdata = os.environ.get("APPDATA")
    if appdata:
        p = Path(appdata) / APP_NAME
    else:
        p = Path.home() / f".{APP_NAME}"
    p.mkdir(parents=True, exist_ok=True)
    return p


def get_config_file() -> Path:
    return get_config_dir() / "config.json"


DEFAULT_CONFIG: Dict[str, Any] = {
    "enabled": False,
    "temperature_k": 3400,
    "brightness": 1.0,
    "smooth_transitions": True,
    "transition_duration": 0.20,
    "autostart": False,
}


@contextmanager
def config_file_lock(path):
    """Kernel byte lock shared by processes; automatically released on crash."""
    with open(str(path) + '.lock', 'a+b') as lock:
        if lock.seek(0, 2) == 0:
            lock.write(b'0')
            lock.flush()
        deadline = time.monotonic() + 10
        while True:
            lock.seek(0)
            try:
                msvcrt.locking(lock.fileno(), msvcrt.LK_NBLCK, 1)
                break
            except OSError:
                if time.monotonic() >= deadline:
                    raise TimeoutError('Night Light configuration is busy')
                time.sleep(0.02)
        try:
            yield
        finally:
            lock.seek(0)
            msvcrt.locking(lock.fileno(), msvcrt.LK_UNLCK, 1)


class ConfigManager:
    def __init__(self):
        self.file_path = get_config_file()
        self.data: Dict[str, Any] = dict(DEFAULT_CONFIG)
        self._saved_data = dict(DEFAULT_CONFIG)
        self._debounce_timer: Optional[threading.Timer] = None
        self._lock = threading.Lock()
        self.load()
        self._saved_data = dict(self.data)

    def load(self):
        """Loads configuration from JSON file."""
        missing = False
        with self._lock, config_file_lock(self.file_path):
            if self.file_path.exists():
                try:
                    with open(self.file_path, "r", encoding="utf-8") as f:
                        saved = json.load(f)
                        if not isinstance(saved, dict):
                            raise ValueError('Configuration must be an object')
                        self.data.update(saved)
                except Exception as e:
                    print(f"[ConfigManager] Error loading config: {e}")
            else:
                missing = True
        # Save after releasing both locks so the public method can reacquire
        # them in the established order without recursive-lock deadlock.
        if missing:
            self.save_immediate()

    def save_immediate(self):
        """Saves configuration directly to disk."""
        with self._lock, config_file_lock(self.file_path):
            if self._debounce_timer:
                self._debounce_timer.cancel()
                self._debounce_timer = None
            self._save_locked()

    def _save_locked(self):
        """Save while the caller owns both the thread and config-file locks."""
        try:
            self.file_path.parent.mkdir(parents=True, exist_ok=True)
            previous = getattr(self, '_saved_data', {})
            merged = dict(self.data)
            if self.file_path.exists():
                try:
                    disk = json.loads(self.file_path.read_text(encoding='utf-8'))
                    if not isinstance(disk, dict):
                        raise ValueError('Configuration must be an object')
                    merged = disk
                except (ValueError, UnicodeError, RecursionError) as error:
                    # Recheck and quarantine under the same kernel lock as writers.
                    # Windows rename refuses to replace an existing destination.
                    quarantine = self.file_path.with_name(
                        self.file_path.name + '.corrupt-' + secrets.token_hex(16)
                    )
                    self.file_path.rename(quarantine)
                    self.recovery_diagnostic = (
                        f'Corrupt configuration quarantined at {quarantine}: {error}'
                    )
                    print(f'[ConfigManager] {self.recovery_diagnostic}')
            stable_token = merged.get('ipc_token')
            merged.update({k: v for k, v in self.data.items() if k not in previous or previous[k] != v})
            for key in previous.keys() - self.data.keys():
                merged.pop(key, None)
            if isinstance(stable_token, str) and len(stable_token) >= 32 and stable_token.isascii():
                merged['ipc_token'] = stable_token
            fd, tmp_name = tempfile.mkstemp(
                prefix=f".{self.file_path.name}.", suffix=".tmp", dir=self.file_path.parent
            )
            try:
                with os.fdopen(fd, "w", encoding="utf-8") as f:
                    json.dump(merged, f, indent=2)
                    f.flush()
                    os.fsync(f.fileno())
                os.replace(tmp_name, self.file_path)
                self.data = merged
                self._saved_data = dict(merged)
            finally:
                if os.path.exists(tmp_name):
                    os.unlink(tmp_name)
        except Exception as e:
            print(f"[ConfigManager] Error saving config: {e}")
            raise

    def save_debounced(self, delay: float = 0.3):
        """Debounces disk saves so real-time slider dragging has zero stutter."""
        with self._lock:
            if self._debounce_timer:
                self._debounce_timer.cancel()
            self._debounce_timer = threading.Timer(delay, self.save_immediate)
            self._debounce_timer.daemon = True
            self._debounce_timer.start()

    def get(self, key: str, default: Any = None) -> Any:
        return self.data.get(key, default)

    def set(self, key: str, value: Any, save_now: bool = True):
        with self._lock:
            self.data[key] = value
        if save_now:
            self.save_debounced()

    # Windows Autostart Registry
    def is_autostart_enabled(self) -> bool:
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, REG_RUN_PATH, 0, winreg.KEY_READ) as key:
                val, _ = winreg.QueryValueEx(key, APP_NAME)
                return bool(val)
        except FileNotFoundError:
            return False
        except Exception:
            return False

    def set_autostart(self, enable: bool) -> bool:
        if getattr(sys, "frozen", False):
            cmd = f'"{sys.executable}" --background'
        else:
            script_path = Path(__file__).parent / "main.py"
            cmd = f'"{sys.executable}" "{script_path.resolve()}" --background'

        try:
            with winreg.OpenKey(
                winreg.HKEY_CURRENT_USER, REG_RUN_PATH, 0, winreg.KEY_SET_VALUE
            ) as key:
                if enable:
                    winreg.SetValueEx(key, APP_NAME, 0, winreg.REG_SZ, cmd)
                    self.set("autostart", True, save_now=True)
                else:
                    try:
                        winreg.DeleteValue(key, APP_NAME)
                    except FileNotFoundError:
                        pass
                    self.set("autostart", False, save_now=True)
            return True
        except Exception as e:
            print(f"[ConfigManager] Failed to set autostart: {e}")
            return False


config = ConfigManager()


def get_or_create_ipc_token(manager: Optional[ConfigManager] = None) -> str:
    """Return the per-install token used to authenticate localhost commands."""
    target = manager or config
    token = target.get("ipc_token")
    if not isinstance(token, str) or len(token) < 32 or not token.isascii():
        token = secrets.token_urlsafe(32)
    target.set("ipc_token", token, save_now=False)
    target.save_immediate()
    return target.get('ipc_token')
