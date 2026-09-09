"""
Configuration and Windows integration manager for Night Light by HT.
Handles JSON persistence with debouncing to prevent disk stutter during slider dragging.
"""

import json
import os
from pathlib import Path
import secrets
import sys
import threading
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


class ConfigManager:
    def __init__(self):
        self.file_path = get_config_file()
        self.data: Dict[str, Any] = dict(DEFAULT_CONFIG)
        self._debounce_timer: Optional[threading.Timer] = None
        self._lock = threading.Lock()
        self.load()

    def load(self):
        """Loads configuration from JSON file."""
        if self.file_path.exists():
            try:
                with open(self.file_path, "r", encoding="utf-8") as f:
                    saved = json.load(f)
                    self.data.update(saved)
            except Exception as e:
                print(f"[ConfigManager] Error loading config: {e}")
        else:
            self.save_immediate()

    def save_immediate(self):
        """Saves configuration directly to disk."""
        with self._lock:
            if self._debounce_timer:
                self._debounce_timer.cancel()
                self._debounce_timer = None
            try:
                with open(self.file_path, "w", encoding="utf-8") as f:
                    json.dump(self.data, f, indent=2)
            except Exception as e:
                print(f"[ConfigManager] Error saving config: {e}")

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
            cmd = f'"{sys.executable}"'
        else:
            script_path = Path(__file__).parent / "main.py"
            cmd = f'"{sys.executable}" "{script_path.resolve()}"'

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
    if isinstance(token, str) and len(token) >= 32:
        return token

    token = secrets.token_urlsafe(32)
    target.set("ipc_token", token, save_now=False)
    target.save_immediate()
    return token
