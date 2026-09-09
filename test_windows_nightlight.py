import unittest
from unittest.mock import patch

from windows_nightlight import get_windows_nightlight_status
from nightlight_engine import NightLightEngine


class _Key:
    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False


class WindowsNightLightTests(unittest.TestCase):
    def test_detects_enabled_cloudstore_payload(self):
        data = bytearray(b"CB\x01\x00" + bytes(39))
        data[18] = 0x15
        with patch("windows_nightlight.winreg.OpenKey", return_value=_Key()), patch(
            "windows_nightlight.winreg.QueryValueEx",
            return_value=(bytes(data), 3),
        ):
            self.assertTrue(get_windows_nightlight_status().is_enabled)

    def test_detects_disabled_cloudstore_payload(self):
        data = bytearray(b"CB\x01\x00" + bytes(39))
        data[18] = 0x13
        with patch("windows_nightlight.winreg.OpenKey", return_value=_Key()), patch(
            "windows_nightlight.winreg.QueryValueEx",
            return_value=(bytes(data), 3),
        ):
            self.assertFalse(get_windows_nightlight_status().is_enabled)

    def test_detects_default_disabled_cloudstore_payload(self):
        data = bytearray(b"CB\x01\x00" + bytes(39))
        data[18] = 0x10
        with patch("windows_nightlight.winreg.OpenKey", return_value=_Key()), patch(
            "windows_nightlight.winreg.QueryValueEx",
            return_value=(bytes(data), 3),
        ):
            self.assertFalse(get_windows_nightlight_status().is_enabled)

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
