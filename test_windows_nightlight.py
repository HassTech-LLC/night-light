import unittest
from unittest.mock import patch

from windows_nightlight import get_windows_nightlight_status, parse_cloudstore_state
from nightlight_engine import NightLightEngine


def _blob(text: str) -> bytes:
    return bytes.fromhex(text.replace(" ", ""))


# Labeled fixtures. The first two are the published Bond CompactBinary samples
# from kvnxiao/win-nightlight-cli (older Windows layout that also writes the
# "initialized" field 10, so byte 18 reads 0x13/0x15). The third is a live
# read-only capture from Windows 11 build 26200 with the switch off (no field
# 10, so byte 18 reads 0x10). The fourth is that capture with the ON field
# (inner field 0, ``10 00``) inserted and the list count bumped to 0x12.
OLDER_BUILD_OFF = _blob(
    "43420100 0a020100 2a06 8995fcbe06 2a2b0e13 43420100 d00a02 c614 a9f6e2d3efeae6ed01 00 000000"
)
OLDER_BUILD_ON = _blob(
    "43420100 0a020100 2a06 8995fcbe06 2a2b0e15 43420100 1000 d00a02 c614 a9f6e2d3efeae6ed01 00 000000"
)
BUILD_26200_OFF = _blob(
    "43420100 0a020100 2a06 f28e83d506 2a2b0e10 43420100 c614 e9cd89b5cc80d0ee01 00 000000"
)
BUILD_26200_ON = _blob(
    "43420100 0a020100 2a06 f28e83d506 2a2b0e12 43420100 1000 c614 e9cd89b5cc80d0ee01 00 000000"
)


class _Key:
    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False


class WindowsNightLightTests(unittest.TestCase):
    def test_older_build_fixtures(self):
        self.assertIs(parse_cloudstore_state(OLDER_BUILD_ON).is_enabled, True)
        self.assertIs(parse_cloudstore_state(OLDER_BUILD_OFF).is_enabled, False)

    def test_build_26200_fixtures(self):
        self.assertIs(parse_cloudstore_state(BUILD_26200_ON).is_enabled, True)
        self.assertIs(parse_cloudstore_state(BUILD_26200_OFF).is_enabled, False)

    def test_byte_18_is_not_a_state_marker(self):
        # Same length byte as a real ON payload, but structurally meaningless:
        # a marker-based parser would call this ON; the structural one fails safe.
        data = bytearray(b"CB\x01\x00" + bytes(39))
        data[18] = 0x15
        self.assertIsNone(parse_cloudstore_state(bytes(data)).is_enabled)
        data[18] = 0x13
        self.assertIsNone(parse_cloudstore_state(bytes(data)).is_enabled)

    def test_malformed_payloads_stay_unknown(self):
        for data in (
            OLDER_BUILD_ON[:30],                                   # truncated
            b"CB\x01\x00" + b"\xff" * 30,                          # garbage fields
            OLDER_BUILD_ON.replace(b"\x10\x00", b"\x02\x00"),      # field 0 with wrong type
            b"CB\x02\x00" + OLDER_BUILD_ON[4:],                    # unknown marshaled version
            b"",
        ):
            self.assertIsNone(parse_cloudstore_state(data).is_enabled, data.hex())

    def test_registry_read_uses_parser(self):
        with patch("windows_nightlight.winreg.OpenKey", return_value=_Key()), patch(
            "windows_nightlight.winreg.QueryValueEx",
            return_value=(BUILD_26200_ON, 3),
        ):
            self.assertTrue(get_windows_nightlight_status().is_enabled)
        with patch("windows_nightlight.winreg.OpenKey", return_value=_Key()), patch(
            "windows_nightlight.winreg.QueryValueEx",
            return_value=(BUILD_26200_OFF, 1),  # REG_SZ, not REG_BINARY
        ):
            self.assertIsNone(get_windows_nightlight_status().is_enabled)

    def test_smart_mode_suppresses_widget_matrix_when_native_is_on(self):
        engine = NightLightEngine()
        engine._mag_available = False
        engine.is_enabled = True
        engine.set_windows_nightlight_policy(native_is_active=True)
        self.assertTrue(engine.is_suppressed_by_windows_nightlight)
        engine.set_windows_nightlight_policy(native_is_active=False)
        self.assertFalse(engine.is_suppressed_by_windows_nightlight)

    def test_native_policy_neutralizes_warmth_and_dimming(self):
        class _FakeMagnification:
            def MagSetFullscreenColorEffect(self, _effect):
                return True

        engine = NightLightEngine()
        engine._mag = _FakeMagnification()
        engine._mag_available = True
        engine._mag_initialized = True
        engine.is_enabled = True
        engine.temperature_k = 1200
        engine.brightness = 0.2

        engine.set_windows_nightlight_policy(native_is_active=True)

        self.assertEqual(
            (engine._current_r, engine._current_g, engine._current_b),
            (1.0, 1.0, 1.0),
        )
        engine._mag_available = False


if __name__ == "__main__":
    unittest.main()
