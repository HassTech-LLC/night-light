from display_status import derive_display_status


def test_windows_on_always_pauses_hass_warmth():
    state = derive_display_status(
        app_enabled=True, brightness=1.0, windows_active=True
    )
    assert state.windows_label == "ON"
    assert state.hass_label == "PAUSED"


def test_smart_mode_reports_warmth_as_paused():
    state = derive_display_status(
        app_enabled=True, brightness=1.0, windows_active=True
    )
    assert state.hass_label == "PAUSED"
    assert state.hass_effective is False


def test_windows_on_fully_pauses_ht_even_when_brightness_is_lowered():
    state = derive_display_status(
        app_enabled=True, brightness=0.5, windows_active=True
    )
    assert state.hass_label == "PAUSED"
    assert state.hass_effective is False


def test_unknown_windows_state_is_not_overclaimed():
    state = derive_display_status(
        app_enabled=True, brightness=1.0, windows_active=None
    )
    assert state.windows_label == "UNKNOWN"
    assert state.hass_label == "PAUSED"
    assert state.hass_effective is False
    assert "unconfirmed" in state.summary.lower()


def test_app_off_does_not_claim_windows_is_off():
    state = derive_display_status(
        app_enabled=False, brightness=1.0, windows_active=True
    )
    assert state.hass_label == "OFF"
    assert state.windows_label == "ON"


def test_unknown_backend_is_not_reported_active():
    state=derive_display_status(app_enabled=True,brightness=1,windows_active=False,backend_applied=None)
    assert state.hass_label=='UNKNOWN' and not state.hass_effective


def test_off_does_not_claim_all_other_color_pipelines_are_off():
    state=derive_display_status(app_enabled=False,brightness=1,windows_active=False)
    assert state.summary=='Night Light is off'
