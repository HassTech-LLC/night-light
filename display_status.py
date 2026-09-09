"""Pure presentation state for the Windows + Night Light by HT pipeline."""

from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class DisplayStatus:
    windows_label: str
    windows_active: Optional[bool]
    hass_label: str
    hass_active: bool
    hass_effective: bool
    summary: str
    detail: str


def derive_display_status(
    *,
    app_enabled: bool,
    brightness: float,
    windows_active: Optional[bool],
) -> DisplayStatus:
    """Return honest user-facing state without implying control of Windows."""
    windows_label = (
        "ON" if windows_active is True else "OFF" if windows_active is False else "UNKNOWN"
    )

    if not app_enabled:
        if windows_active is True:
            summary = "Windows Night Light is active"
        elif windows_active is False:
            summary = "No night filter is active"
        else:
            summary = "Night Light by HT is off; Windows status is unconfirmed"
        return DisplayStatus(
            windows_label, windows_active, "OFF", False, False, summary,
            "Night Light by HT is disabled",
        )

    if windows_active is True:
        return DisplayStatus(
            windows_label, windows_active, "PAUSED", True, False,
            "Windows is active; Night Light by HT is fully paused",
            "Turn Windows Night Light off to use the HT filter",
        )

    if windows_active is None:
        return DisplayStatus(
            windows_label, windows_active, "PAUSED", True, False,
            "Windows status is unconfirmed; Night Light by HT is paused",
            "HT waits for confirmation that Windows Night Light is off",
        )

    return DisplayStatus(
        windows_label, windows_active, "ON", True, True,
        "Night Light by HT is active",
        "Windows Night Light is off",
    )
