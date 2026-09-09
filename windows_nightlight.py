"""Read-only detection for Windows' built-in Night Light state.

Windows does not expose a public desktop API for the inbox Night Light switch.
Its current state is stored in the per-user CloudStore payload below. This
widget only reads the payload; it never changes the Windows setting.
"""

from dataclasses import dataclass
from typing import Optional
import winreg


STATE_KEY = (
    r"Software\Microsoft\Windows\CurrentVersion\CloudStore\Store\DefaultAccount\Current"
    r"\default$windows.data.bluelightreduction.bluelightreductionstate"
    r"\windows.data.bluelightreduction.bluelightreductionstate"
)
STATE_VALUE = "Data"
_HEADER = b"CB\x01\x00"
_STATE_OFFSET = 18
_ENABLED_MARKER = 0x15
_DISABLED_MARKER = 0x13
# Unknown markers (including 0x10) remain fail-safe until independently labeled.
_CURRENT_ENABLED_MARKERS = frozenset((0x15,))


@dataclass(frozen=True)
class WindowsNightLightStatus:
    is_enabled: Optional[bool]
    detail: str

    @property
    def is_available(self) -> bool:
        return self.is_enabled is not None


def parse_cloudstore_state(data: bytes) -> WindowsNightLightStatus:
    """Decode a known CloudStore record without guessing unknown formats."""
    if not isinstance(data, bytes) or len(data) <= _STATE_OFFSET or data[:4] != _HEADER:
        return WindowsNightLightStatus(None, "Windows Night Light state format is unsupported")
    marker = data[_STATE_OFFSET]
    if marker in _CURRENT_ENABLED_MARKERS:
        return WindowsNightLightStatus(True, "Windows Night Light is on")
    if marker == _DISABLED_MARKER:
        return WindowsNightLightStatus(False, "Windows Night Light is off")
    return WindowsNightLightStatus(None, "Windows Night Light state is unknown")


def get_windows_nightlight_status() -> WindowsNightLightStatus:
    """Returns the current native Night Light state, or unknown safely."""
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, STATE_KEY) as key:
            data, value_type = winreg.QueryValueEx(key, STATE_VALUE)
    except FileNotFoundError:
        return WindowsNightLightStatus(None, "Windows Night Light state is unavailable")
    except OSError as exc:
        return WindowsNightLightStatus(None, f"Could not read Windows Night Light ({exc})")

    if value_type != winreg.REG_BINARY or not isinstance(data, bytes):
        return WindowsNightLightStatus(None, "Windows Night Light returned an unsupported state")
    return parse_cloudstore_state(data)
