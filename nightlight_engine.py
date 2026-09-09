"""
Night Light Display Engine
Handles color temperature (Kelvin) calculations, software brightness dimming,
hardware-accelerated Windows Magnification color matrix transformations, and smooth 60fps transitions.
"""

import atexit
import ctypes
from ctypes import wintypes
import math
import os
import time
from typing import Callable, Optional, Tuple


class MAGCOLOREFFECT(ctypes.Structure):
    _fields_ = [("transform", (ctypes.c_float * 5) * 5)]


def kelvin_to_rgb(kelvin: float) -> Tuple[float, float, float]:
    """
    Converts a color temperature in Kelvin (1000K - 6500K) to normalized (R, G, B) multipliers.
    Based on Tanner Helland's algorithm / Planckian locus approximation.
    6500K = (1.0, 1.0, 1.0) (Neutral standard daylight D65).
    Lower Kelvin = Warmer amber/red, reduced blue.
    """
    kelvin = max(1000.0, min(6500.0, float(kelvin)))
    if kelvin >= 6500.0:
        return (1.0, 1.0, 1.0)

    temp = kelvin / 100.0

    # Calculate Red
    if temp <= 66.0:
        red = 255.0
    else:
        red = temp - 60.0
        red = 329.698727446 * (red ** -0.1332047592)
        red = max(0.0, min(255.0, red))

    # Calculate Green
    if temp <= 66.0:
        green = temp
        green = 99.4708025861 * math.log(green) - 161.1195681661
        green = max(0.0, min(255.0, green))
    else:
        green = temp - 60.0
        green = 288.1221695283 * (green ** -0.0755148492)
        green = max(0.0, min(255.0, green))

    # Calculate Blue
    if temp >= 65.0:
        blue = 255.0
    elif temp <= 19.0:
        blue = 0.0
    else:
        blue = temp - 10.0
        blue = 138.5177312231 * math.log(blue) - 305.0447927307
        blue = max(0.0, min(255.0, blue))

    return (
        max(0.0, min(1.0, red / 255.0)),
        max(0.0, min(1.0, green / 255.0)),
        max(0.0, min(1.0, blue / 255.0)),
    )


class NightLightEngine:
    def __init__(self):
        self._mag_available = False
        self._mag_initialized = False
        self._transition_id: int = 0
        self._dispatcher: Optional[Callable[[int, Callable], None]] = None

        # State tracking
        self.is_enabled: bool = False
        self.temperature_k: int = 3400  # Default warm amber
        self.brightness: float = 1.0    # 1.0 = 100%
        self.transition_duration: float = 0.20  # Fast, smooth 200ms transitions
        self._windows_nightlight_active: bool = False
        self.is_applied: bool = False

        # Current applied color factors
        self._current_r: float = 1.0
        self._current_g: float = 1.0
        self._current_b: float = 1.0

        self._init_backend()
        atexit.register(self.reset_to_neutral)

    def set_gui_dispatcher(self, dispatcher: Callable[[int, Callable], None]):
        """Sets a timer dispatcher (root.after) to run animation frames on the GUI thread."""
        self._dispatcher = dispatcher

    def _init_backend(self):
        """Initializes the Windows Magnification API backend."""
        if os.environ.get("NIGHT_LIGHT_BY_HT_DISABLE_DISPLAY_BACKEND") == "1":
            return
        try:
            self._mag = ctypes.windll.magnification
            self._mag.MagInitialize.restype = wintypes.BOOL
            self._mag.MagUninitialize.restype = wintypes.BOOL
            self._mag.MagSetFullscreenColorEffect.restype = wintypes.BOOL
            self._mag.MagSetFullscreenColorEffect.argtypes = [ctypes.POINTER(MAGCOLOREFFECT)]

            if self._mag.MagInitialize():
                self._mag_initialized = True
                self._mag_available = True
            else:
                self._mag_available = False
        except Exception as e:
            print(f"[NightLightEngine] Failed to initialize Magnification API: {e}")
            self._mag_available = False

    def _apply_matrix(self, r: float, g: float, b: float) -> bool:
        """Applies an RGB transformation matrix to the entire desktop."""
        if self.is_enabled and self.is_suppressed_by_windows_nightlight:
            # One warmth pipeline only. When Windows Night Light is active the
            # HT matrix is fully neutral, including its software dimming.
            r = g = b = 1.0
        if not self._mag_available:
            self.is_applied = False
            return False

        if not self._mag_initialized:
            self._mag.MagInitialize()
            self._mag_initialized = True

        effect = MAGCOLOREFFECT()
        effect.transform[0][0] = max(0.0, min(1.0, r))
        effect.transform[1][1] = max(0.0, min(1.0, g))
        effect.transform[2][2] = max(0.0, min(1.0, b))
        effect.transform[3][3] = 1.0  # Alpha
        effect.transform[4][4] = 1.0  # Homogeneous coordinate

        res = self._mag.MagSetFullscreenColorEffect(ctypes.byref(effect))
        if res:
            self.is_applied = True
            self._current_r = r
            self._current_g = g
            self._current_b = b
        if not res:
            self.is_applied = False
        return bool(res)

    def _get_target_rgb(self, enabled: bool, temp_k: int, brightness: float) -> Tuple[float, float, float]:
        """Calculates target RGB factors."""
        if not enabled:
            return (1.0, 1.0, 1.0)
        
        base_r, base_g, base_b = kelvin_to_rgb(temp_k)
        br = max(0.1, min(1.0, brightness))
        return (base_r * br, base_g * br, base_b * br)

    @property
    def is_suppressed_by_windows_nightlight(self) -> bool:
        return self._windows_nightlight_active

    def set_windows_nightlight_policy(self, native_is_active: bool):
        """Always avoid double-warming over Windows Night Light."""
        self._windows_nightlight_active = bool(native_is_active)
        if self.is_enabled:
            tr, tg, tb = self._get_target_rgb(True, self.temperature_k, self.brightness)
            self._apply_matrix(tr, tg, tb)

    def set_strength_live(self, strength_pct: float):
        """
        Ultra-fast (0.002ms) live slider drag handler.
        0% = 6500K (Daylight / OFF)
        100% = 1200K (Max warm candle)
        """
        self._transition_id += 1  # Cancel any ongoing smooth transition
        pct = max(0.0, min(100.0, float(strength_pct)))
        
        if pct <= 0.5:
            self.is_enabled = False
            self.temperature_k = 6500
            self._apply_matrix(1.0, 1.0, 1.0)
        else:
            self.is_enabled = True
            # Map 0..100% to 6500K..1200K
            k = int(6500 - (pct / 100.0) * (6500 - 1200))
            self.temperature_k = k
            tr, tg, tb = self._get_target_rgb(True, self.temperature_k, self.brightness)
            self._apply_matrix(tr, tg, tb)

    def set_brightness_live(self, brightness_pct: float):
        """Ultra-fast live brightness slider handler."""
        self._transition_id += 1
        br = max(0.20, min(1.0, float(brightness_pct) / 100.0))
        self.brightness = br
        if self.is_enabled:
            tr, tg, tb = self._get_target_rgb(True, self.temperature_k, self.brightness)
            self._apply_matrix(tr, tg, tb)

    def set_state(
        self,
        enabled: Optional[bool] = None,
        temperature_k: Optional[int] = None,
        brightness: Optional[float] = None,
        smooth: bool = True,
        on_complete: Optional[Callable[[], None]] = None,
    ):
        """Updates Night Light state with smooth 60fps fade."""
        if enabled is not None:
            self.is_enabled = bool(enabled)
        if temperature_k is not None:
            self.temperature_k = int(temperature_k)
        if brightness is not None:
            self.brightness = float(brightness)

        target_r, target_g, target_b = self._get_target_rgb(
            self.is_enabled, self.temperature_k, self.brightness
        )

        self._transition_id += 1
        my_id = self._transition_id
        start_r = self._current_r
        start_g = self._current_g
        start_b = self._current_b
        duration = self.transition_duration if smooth else 0.0

        if not smooth or duration <= 0.01 or not self._dispatcher:
            self._apply_matrix(target_r, target_g, target_b)
            if on_complete:
                on_complete()
            return

        start_time = time.perf_counter()
        frame_ms = 16

        def _step():
            if my_id != self._transition_id:
                return

            elapsed = time.perf_counter() - start_time
            t = min(1.0, elapsed / duration) if duration > 0 else 1.0
            ease = 1.0 - (1.0 - t) ** 3

            cur_r = start_r + (target_r - start_r) * ease
            cur_g = start_g + (target_g - start_g) * ease
            cur_b = start_b + (target_b - start_b) * ease

            self._apply_matrix(cur_r, cur_g, cur_b)

            if t < 1.0 and my_id == self._transition_id:
                self._dispatcher(frame_ms, _step)
            else:
                if my_id == self._transition_id:
                    self._apply_matrix(target_r, target_g, target_b)
                    if on_complete:
                        on_complete()

        self._dispatcher(frame_ms, _step)

    def toggle(self, smooth: bool = True, on_complete: Optional[Callable[[], None]] = None) -> bool:
        """Toggles Night Light ON/OFF."""
        new_state = not self.is_enabled
        self.set_state(enabled=new_state, smooth=smooth, on_complete=on_complete)
        return new_state

    def reset_to_neutral(self):
        """Immediately restores screen color to normal 100% daylight."""
        self._transition_id += 1
        self.is_enabled = False
        self.is_applied = False
        try:
            if self._mag_available:
                effect = MAGCOLOREFFECT()
                for i in range(5):
                    effect.transform[i][i] = 1.0
                self._mag.MagSetFullscreenColorEffect(ctypes.byref(effect))
                self._current_r = 1.0
                self._current_g = 1.0
                self._current_b = 1.0
                self._mag.MagUninitialize()
                self._mag_initialized = False
        except Exception:
            pass


engine = NightLightEngine()
