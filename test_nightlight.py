"""
Unit and integration tests for Night Light by HT.
"""

import unittest

from nightlight_engine import kelvin_to_rgb, NightLightEngine
from config_manager import ConfigManager, get_or_create_ipc_token
import icons


class TestNightLight(unittest.TestCase):
    def test_kelvin_to_rgb_ranges(self):
        # 6500K should be neutral (1.0, 1.0, 1.0)
        r, g, b = kelvin_to_rgb(6500)
        self.assertAlmostEqual(r, 1.0, places=2)
        self.assertAlmostEqual(g, 1.0, places=2)
        self.assertAlmostEqual(b, 1.0, places=2)

        # 3400K (Warm) should have full red, reduced green, and significantly reduced blue
        r, g, b = kelvin_to_rgb(3400)
        self.assertAlmostEqual(r, 1.0, places=2)
        self.assertTrue(g < 0.85 and g > 0.65)
        self.assertTrue(b < 0.60 and b > 0.40)

        # 1900K (Candle) should have very low blue
        r, g, b = kelvin_to_rgb(1900)
        self.assertAlmostEqual(r, 1.0, places=2)
        self.assertTrue(g < 0.60)
        self.assertTrue(b < 0.10)

        # Values should always stay bounded [0.0, 1.0]
        for k in range(500, 7000, 200):
            kr, kg, kb = kelvin_to_rgb(k)
            self.assertTrue(0.0 <= kr <= 1.0)
            self.assertTrue(0.0 <= kg <= 1.0)
            self.assertTrue(0.0 <= kb <= 1.0)

    def test_engine_state(self):
        eng = NightLightEngine()
        self.assertFalse(eng.is_enabled)
        
        # Test toggle
        new_state = eng.toggle(smooth=False)
        self.assertTrue(new_state)
        self.assertTrue(eng.is_enabled)

        # Test set state
        eng.set_state(temperature_k=2500, brightness=0.8, smooth=False)
        self.assertEqual(eng.temperature_k, 2500)
        self.assertEqual(eng.brightness, 0.8)

        # Test reset
        eng.reset_to_neutral()

    def test_config_manager(self):
        cfg = ConfigManager()
        cfg.set("test_key", 12345, save_now=False)
        self.assertEqual(cfg.get("test_key"), 12345)

    def test_ipc_token_is_persistent_and_unpredictable_length(self):
        cfg = ConfigManager()
        first = get_or_create_ipc_token(cfg)
        second = get_or_create_ipc_token(cfg)
        self.assertEqual(first, second)
        self.assertGreaterEqual(len(first), 32)

    def test_icon_generation(self):
        img_active = icons.create_moon_icon(size=32, active=True)
        self.assertEqual(img_active.size, (32, 32))
        self.assertEqual(img_active.mode, "RGBA")

        img_inactive = icons.create_moon_icon(size=32, active=False)
        self.assertEqual(img_inactive.size, (32, 32))
        self.assertEqual(img_inactive.mode, "RGBA")


if __name__ == "__main__":
    unittest.main()
