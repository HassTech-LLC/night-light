"""Pure presentation state for the Windows + Night Light pipeline."""

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
    backend_applied: Optional[bool] = True,
    output_fault: Optional[str] = None,
) -> DisplayStatus:
    """Return honest user-facing state without implying control of Windows."""
    windows_label = (
        "ON" if windows_active is True else "OFF" if windows_active is False else "UNKNOWN"
    )

    if output_fault:
        external=output_fault=='external_conflict'
        detail=('Another display transform was detected. Close the other color tool, then choose Retry display.'
                if external else 'The display connection needs attention. Choose Retry display after checking Windows.')
        summary=('Another display transform was detected' if external else 'Display adjustment is unconfirmed')
        if not app_enabled:summary='Night Light is off; '+summary[0].lower()+summary[1:]
        return DisplayStatus(windows_label,windows_active,'PAUSED' if app_enabled else 'OFF',
                             app_enabled,False,summary,detail)

    if not app_enabled:
        if windows_active is True:
            summary = "Windows Night Light is active"
        elif windows_active is False:
            summary = "Night Light is off"
        else:
            summary = "Night Light is off; Windows status is unconfirmed"
        return DisplayStatus(
            windows_label, windows_active, "OFF", False, False, summary,
            "Night Light is disabled",
        )

    if windows_active is True:
        return DisplayStatus(
            windows_label, windows_active, "PAUSED", True, False,
            "Windows is active; Night Light is fully paused",
            "Turn Windows Night Light off to use the Night Light filter",
        )

    if windows_active is None:
        return DisplayStatus(
            windows_label, windows_active, "PAUSED", True, False,
            "Windows status is unconfirmed; Night Light is paused",
            "Night Light waits for confirmation that Windows Night Light is off",
        )

    if backend_applied is False:
        return DisplayStatus(
            windows_label, windows_active, "FAILED", True, False,
            "Night Light could not apply the display filter",
            "The display backend rejected the requested transform",
        )

    if backend_applied is not True:
        return DisplayStatus(
            windows_label, windows_active, "UNKNOWN", True, False,
            "Night Light display adjustment is unconfirmed",
            "No confirmed display-backend result is available",
        )

    return DisplayStatus(
        windows_label, windows_active, "ON", True, True,
        "Night Light is active",
        "Windows Night Light is off",
    )
