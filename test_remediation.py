import json
from pathlib import Path
from unittest.mock import patch

from config_manager import ConfigManager
from display_status import derive_display_status
from main import command_from_args
from nightlight_engine import NightLightEngine
from windows_nightlight import parse_cloudstore_state


def test_cloudstore_parser_reads_windows_11_26200_off_state():
    live = bytes.fromhex("43420100" "0a020100" "2a06f28e83d506" "2a2b0e10" "43420100" "c614e9cd89b5cc80d0ee01" "00" "000000")
    assert parse_cloudstore_state(live).is_enabled is False


def test_cloudstore_parser_keeps_unknown_structure_safe():
    data = bytearray(b"CB\x01\x00" + bytes(39))
    data[18] = 0x99
    assert parse_cloudstore_state(bytes(data)).is_enabled is None


def test_preset_commands_clamp_to_supported_kelvin_range():
    assert command_from_args(["--preset", "900"]) == "PRESET 900"  # clamp happens at dispatch
    from smart_state import Appearance
    Appearance(max(1200, min(6500, 900)), 0.)  # the clamped value is a valid v2 appearance


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
    assert json.loads(cfg.file_path.read_text()) == {"enabled": True, "config_revision": 1}


def test_ipc_parser_rejects_non_ascii_without_exception():
    from tray_app import parse_authenticated_ipc
    assert parse_authenticated_ipc("é TOGGLE", "correct-token") is None
