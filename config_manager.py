"""
Configuration and Windows integration manager for Night Light by HT.
Handles JSON persistence with debouncing to prevent disk stutter during slider dragging.
"""

import json
from copy import deepcopy
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
from private_config_files import copy_file_access
from config_paths import config_directory


APP_NAME = "NightLightWidget"
REG_RUN_PATH = r"Software\Microsoft\Windows\CurrentVersion\Run"


def get_config_dir() -> Path:
    """Returns the persistent configuration directory in %APPDATA%."""
    p = config_directory()
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
            try:
                lock.write(b'0')
                lock.flush()
            except (PermissionError, OSError):
                pass
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
        self.automatic_output_blocked = False
        self.recovered_unclean_session = False
        self.session_id = None
        self.owner_commit_pending = False
        self.created_new = False
        self.load()
        self._saved_data = dict(self.data)

    def load(self):
        """Loads configuration from JSON file."""
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
                # Do not release/reacquire the kernel lock between observing
                # absence and creating the file: another starter could create
                # a legacy config in that gap. The locked primitive does not
                # recursively acquire either lock.
                self._save_locked()
                self.created_new = True

    def save_immediate(self):
        """Saves configuration directly to disk."""
        with self._lock, config_file_lock(self.file_path):
            if self._debounce_timer:
                self._debounce_timer.cancel()
                self._debounce_timer = None
            self._save_locked()

    def transactional_update(self, patch, expected_revision=None, *, before_commit=None):
        """Persist a staged update before exposing it to the runtime controller.

        Keep pending unrelated edits on failure. A pending debounce waits for
        this lock and can only see the restored state, never a failed draft.
        """
        if before_commit is not None and not callable(before_commit):
            raise ValueError('Invalid commit guard.')
        with self._lock, config_file_lock(self.file_path):
            if expected_revision is not None:
                if type(expected_revision) is not int or expected_revision < 0:
                    raise ValueError('Invalid settings revision.')
                disk = json.loads(self.file_path.read_text(encoding='utf-8'))
                if not isinstance(disk, dict) or disk.get('config_revision', 0) != expected_revision:
                    raise ValueError('Settings changed. Reload the saved settings before trying again.')
            previous_data = self.data
            previous_saved = self._saved_data
            self.data = deepcopy(previous_data)
            self.data.update(deepcopy(patch))
            try:
                if before_commit is None:
                    self._save_locked()
                else:
                    self._save_locked(before_commit=before_commit)
            except Exception:
                self.data = previous_data
                self._saved_data = previous_saved
                raise
            if self._debounce_timer:
                self._debounce_timer.cancel()
                self._debounce_timer = None

    def transactional_update_isolated(self, patch, expected_revision=None, *, before_commit=None):
        """Worker-safe staging: readers see only the last durably committed data.

        Like transactional_update, merge/persist under both writer locks. Unlike
        the legacy synchronous path, never expose a temporary candidate through
        self.data while disk I/O is pending. No native/UI callbacks are allowed.
        """
        with self._lock, config_file_lock(self.file_path):
            if before_commit is not None:
                before_commit()
            if expected_revision is not None:
                if type(expected_revision) is not int or expected_revision < 0:
                    raise ValueError('Invalid settings revision.')
                disk=json.loads(self.file_path.read_text(encoding='utf-8'))
                if not isinstance(disk,dict) or disk.get('config_revision',0)!=expected_revision:
                    raise ValueError('Settings changed. Reload before saving.')
            candidate=deepcopy(self.data)
            candidate.update(deepcopy(patch))
            revision=self._save_locked(before_commit=before_commit,candidate=candidate)
            if self._debounce_timer:
                self._debounce_timer.cancel()
                self._debounce_timer=None
            return revision

    def _save_locked(self, *, before_commit=None, candidate=None):
        """Save while the caller owns both the thread and config-file locks."""
        try:
            self.file_path.parent.mkdir(parents=True, exist_ok=True)
            previous = getattr(self, '_saved_data', {})
            source = self.data if candidate is None else candidate
            merged = dict(source)
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
            disk_revision = merged.get('config_revision', 0)
            if type(disk_revision) is not int or disk_revision < 0:
                disk_revision = 0
            original = dict(merged)
            merged.update({k: v for k, v in source.items() if k not in previous or previous[k] != v})
            for key in previous.keys() - source.keys():
                merged.pop(key, None)
            if isinstance(stable_token, str) and len(stable_token) >= 32 and stable_token.isascii():
                merged['ipc_token'] = stable_token
            merged['config_revision'] = disk_revision
            if merged != original:
                merged['config_revision'] = disk_revision + 1
            fd, tmp_name = tempfile.mkstemp(
                prefix=f".{self.file_path.name}.", suffix=".tmp", dir=self.file_path.parent
            )
            try:
                with os.fdopen(fd, "w", encoding="utf-8") as f:
                    if self.file_path.exists():
                        copy_file_access(self.file_path,tmp_name)
                    json.dump(merged, f, indent=2)
                    f.flush()
                    os.fsync(f.fileno())
                # Owner-thread guard runs after staging, immediately before the
                # atomic replace. It must not call config methods (locks held).
                if before_commit is not None:
                    before_commit()
                os.replace(tmp_name, self.file_path)
                self.data = merged
                self._saved_data = dict(merged)
                return merged['config_revision']
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

    def _write_session_record(self, record):
        """Atomic, credential-free recovery receipt in the private config folder."""
        path = self.file_path.with_name('session-recovery.json')
        fd, name = tempfile.mkstemp(prefix='.session-', suffix='.tmp', dir=path.parent)
        try:
            with os.fdopen(fd, 'w', encoding='utf-8') as stream:
                json.dump(record, stream)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(name, path)
        finally:
            if os.path.exists(name):
                os.unlink(name)

    def begin_session(self):
        """Called only by the single resident owner, before restoring output."""
        self.session_id = secrets.token_hex(16)
        path = self.file_path.with_name('session-recovery.json')
        self.recovered_unclean_session = False
        try:
            if path.exists():
                try:
                    record = json.loads(path.read_text(encoding='utf-8'))
                    self.recovered_unclean_session = not (
                        isinstance(record, dict) and record.get('version') == 1
                        and record.get('state') == 'closed'
                        and record.get('config_revision') == self.get('config_revision', 0)
                    )
                except (ValueError, UnicodeError, RecursionError):
                    self.recovered_unclean_session = True
            if self.recovered_unclean_session:
                self.transactional_update(self.off_patch())
            self._write_session_record({'version':1,'state':'open','session_id':self.session_id})
            self.automatic_output_blocked = False
            return True
        except OSError:
            self.automatic_output_blocked = True
            # Even if storage is unavailable, no previous automatic intent runs.
            for key,value in self.off_patch().items():
                self.set(key, value, False)
            return False

    def off_patch(self):
        """Neutral intent for both schemas; retain chosen appearance/settings."""
        patch = {'enabled':False,'smart_enabled':False,'smart_hold_until':0}
        if self.get('schema_version') == 2 or 'intent_v2' in self.data:
            saved = self.get('intent_v2')
            intent = deepcopy(saved) if isinstance(saved,dict) else {}
            intent['mode'] = 'off'
            patch.update(intent_v2=intent, override_v2=None)
        return patch

    def finish_session(self):
        """A clean receipt follows, never precedes, durable final preferences."""
        if self.owner_commit_pending:
            raise OSError('Final owner intent is not durably confirmed. Recovery must remain open.')
        self.save_immediate()
        self._write_session_record({'version':1,'state':'closed','session_id':self.session_id,
                                    'config_revision':self.get('config_revision',0)})

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
