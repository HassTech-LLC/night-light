import unittest
from unittest.mock import patch

from windows_nightlight import get_windows_nightlight_status, parse_cloudstore_state
from nightlight_engine import NightLightEngine


def _blob(text: str) -> bytes:
    return bytes.fromhex(text.replace(" ", ""))


# Published Bond CompactBinary samples from kvnxiao/win-nightlight-cli.
PUBLISHED_OFF = _blob(
    "43420100 0a020100 2a06 8995fcbe06 2a2b0e13 43420100 d00a02 c614 a9f6e2d3efeae6ed01 00 000000"
)
PUBLISHED_ON = _blob(
    "43420100 0a020100 2a06 8995fcbe06 2a2b0e15 43420100 1000 d00a02 c614 a9f6e2d3efeae6ed01 00 000000"
)

# Live read-only captures from Windows 11 build 26200 on 2026-09-15, taken by
# toggling the Windows switch and reading the registry between states. These
# are the paired ground truth the earlier audits said was missing.
#
# Three distinct shapes appear on one machine, which is why byte 18 must never
# be read as a state marker: it is the inner payload's length.
#
#   38 bytes, byte 18 = 0x10  off, and never toggled since the profile existed
#                             (no field 10 "initialized" marker yet)
#   43 bytes, byte 18 = 0x15  on   (field 0 present, and Windows adds field 10)
#   41 bytes, byte 18 = 0x13  off, after a toggle cycle (field 10 now present)
LIVE_26200_OFF_PRISTINE = _blob(
    "43420100 0a020100 2a06 f28e83d506 2a2b0e10 43420100 c614 e9cd89b5cc80d0ee01 00 000000"
)
LIVE_26200_ON = _blob(
    "43420100 0a020100 2a06 f2d3a6d506 2a2b0e15 43420100 1000 d00a02 c614 85e2f8db87aad1ee01 00 000000"
)
LIVE_26200_OFF_AFTER_TOGGLE = _blob(
    "43420100 0a020100 2a06 fad3a6d506 2a2b0e13 43420100 d00a02 c614 9399ac8288aad1ee01 00 000000"
)


class _Key:
    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False


class WindowsNightLightTests(unittest.TestCase):
    def test_published_fixtures(self):
        self.assertIs(parse_cloudstore_state(PUBLISHED_ON).is_enabled, True)
        self.assertIs(parse_cloudstore_state(PUBLISHED_OFF).is_enabled, False)

    def test_live_build_26200_captures(self):
        """Paired ground truth: the same machine, read either side of a toggle."""
        self.assertIs(parse_cloudstore_state(LIVE_26200_ON).is_enabled, True)
        self.assertIs(parse_cloudstore_state(LIVE_26200_OFF_PRISTINE).is_enabled, False)
        self.assertIs(parse_cloudstore_state(LIVE_26200_OFF_AFTER_TOGGLE).is_enabled, False)

    def test_payload_length_byte_varies_across_states_on_one_machine(self):
        """Byte 18 is a length. Three lengths, two states, one Windows build."""
        lengths = {
            blob[18]
            for blob in (LIVE_26200_OFF_PRISTINE, LIVE_26200_ON, LIVE_26200_OFF_AFTER_TOGGLE)
        }
        self.assertEqual(lengths, {0x10, 0x15, 0x13})
        # Two different lengths both mean off, so length alone cannot decide state.
        self.assertIs(parse_cloudstore_state(LIVE_26200_OFF_PRISTINE).is_enabled, False)
        self.assertIs(parse_cloudstore_state(LIVE_26200_OFF_AFTER_TOGGLE).is_enabled, False)

    def test_unknown_length_byte_is_still_decoded_structurally(self):
        """A build that omits field 10 while on would emit 0x12, not 0x15.

        No shipping build is known to do this, but the parser must not depend on
        the set of lengths observed so far: an unrecognized length previously
        meant "unknown", which pauses the filter indefinitely.
        """
        synthetic_on = _blob(
            "43420100 0a020100 2a06 f28e83d506 2a2b0e12 43420100 1000 c614 e9cd89b5cc80d0ee01 00 000000"
        )
        self.assertEqual(synthetic_on[18], 0x12)
        self.assertIs(parse_cloudstore_state(synthetic_on).is_enabled, True)

    def test_a_length_byte_alone_proves_nothing(self):
        # Right length byte, no valid Bond structure behind it: fail safe.
        data = bytearray(b"CB\x01\x00" + bytes(39))
        for marker in (0x15, 0x13, 0x10):
            data[18] = marker
            self.assertIsNone(parse_cloudstore_state(bytes(data)).is_enabled)

    def test_malformed_payloads_stay_unknown(self):
        for data in (
            PUBLISHED_ON[:30],                                  # truncated
            b"CB\x01\x00" + b"\xff" * 30,                       # garbage fields
            PUBLISHED_ON.replace(b"\x10\x00", b"\x02\x00"),     # field 0 with wrong type
            b"CB\x02\x00" + PUBLISHED_ON[4:],                   # unknown marshaled version
            b"",
        ):
            self.assertIsNone(parse_cloudstore_state(data).is_enabled, data.hex())

    def test_registry_read_uses_parser(self):
        with patch("windows_nightlight.winreg.OpenKey", return_value=_Key()), patch(
            "windows_nightlight.winreg.QueryValueEx",
            return_value=(LIVE_26200_ON, 3),
        ):
            self.assertTrue(get_windows_nightlight_status().is_enabled)
        with patch("windows_nightlight.winreg.OpenKey", return_value=_Key()), patch(
            "windows_nightlight.winreg.QueryValueEx",
            return_value=(LIVE_26200_OFF_PRISTINE, 1),  # REG_SZ, not REG_BINARY
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
