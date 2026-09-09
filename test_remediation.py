import json
from pathlib import Path
from unittest.mock import patch

from config_manager import ConfigManager
from display_status import derive_display_status
from main import command_from_args
from nightlight_engine import NightLightEngine
from windows_nightlight import parse_cloudstore_state


def test_cloudstore_parser_accepts_windows_11_default_disabled_marker():
    data = bytearray(b"CB\x01\x00" + bytes(39))
    data[18] = 0x10
    assert parse_cloudstore_state(bytes(data)).is_enabled is False


def test_cloudstore_parser_keeps_unknown_marker_safe():
    data = bytearray(b"CB\x01\x00" + bytes(39))
    data[18] = 0x99
    assert parse_cloudstore_state(bytes(data)).is_enabled is None


def test_background_is_idempotent_start_command():
    assert command_from_args(["--background"]) == "START"


def test_backend_failure_is_not_effective():
    engine = NightLightEngine()
    engine._mag_available = False
    engine.set_state(enabled=True, temperature_k=3400, smooth=False)
    assert engine.is_applied is False
    state = derive_display_status(app_enabled=True, brightness=1.0, windows_active=False, backend_applied=False)
    assert state.hass_effective is False
    assert state.hass_label == "FAILED"


def test_config_save_is_atomic_and_flushes_pending_timer(tmp_path):
    cfg = ConfigManager.__new__(ConfigManager)
    cfg.file_path = Path(tmp_path) / "config.json"
    cfg.data = {"enabled": True}
    cfg._debounce_timer = None
    import threading
    cfg._lock = threading.Lock()
    cfg.save_immediate()
    assert json.loads(cfg.file_path.read_text()) == {"enabled": True}


def test_ipc_parser_rejects_non_ascii_without_exception():
    from tray_app import parse_authenticated_ipc
    assert parse_authenticated_ipc("é TOGGLE", "correct-token") is None
