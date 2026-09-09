"""Actual CTk layout and keyboard checks, with all OS integrations stubbed."""
import json
import os
from pathlib import Path
import time
import pytest
import customtkinter as ctk
from PIL import ImageGrab
from config_manager import config
from display_status import derive_display_status
from ui_flyout import ModernFlyout


def descendants(widget):
    for child in widget.winfo_children():
        yield child
        yield from descendants(child)


def pump(root, seconds=0.05):
    until = time.monotonic() + seconds
    while time.monotonic() < until:
        root.update()
        time.sleep(0.01)


@pytest.fixture(scope='module')
def tk_root():
    ctk.deactivate_automatic_dpi_awareness()
    root = ctk.CTk()
    root.withdraw()
    yield root
    root.destroy()


@pytest.fixture
def window(monkeypatch, tk_root):
    monkeypatch.setattr(config, 'is_autostart_enabled', lambda: False)
    monkeypatch.setattr(config, 'set_autostart', lambda enabled: True)
    root = tk_root
    flyout = ModernFlyout(get_display_status=lambda: derive_display_status(app_enabled=False, brightness=1, windows_active=False))
    yield root, flyout
    config.save_immediate()
    flyout.destroy()


def present(root, flyout, scale):
    ctk.set_widget_scaling(scale)
    ctk.set_window_scaling(scale)
    flyout.deiconify()
    pump(root, 1.15)
    flyout.geometry(f'{flyout.flyout_width}x{flyout.flyout_height}+0+0')
    pump(root, 0.2)
    assert flyout.winfo_width() == round(flyout.flyout_width * scale)
    assert flyout.winfo_height() == round(flyout.flyout_height * scale)


@pytest.mark.parametrize('scale', [1, 1.25, 1.5, 2])
def test_footer_controls_are_visible(window, scale):
    root, flyout = window
    present(root, flyout, scale)
    controls = [w for w in descendants(flyout) if isinstance(w, (ctk.CTkButton, ctk.CTkCheckBox, ctk.CTkSlider))]
    footer = [w for w in controls if not isinstance(w, ctk.CTkSlider) and w.cget('text') in ('Start with Windows', 'Quit App', 'Quit Night Light')]
    assert len(footer) == 2
    for w in controls:
        assert w.winfo_viewable() and w.winfo_width() > 1 and w.winfo_height() > 1, str(w)
        assert w.winfo_rooty() + w.winfo_height() <= flyout.winfo_rooty() + flyout.winfo_height(), str(w)


def test_tab_reaches_controls_and_slider_keys_persist(window):
    root, flyout = window
    present(root, flyout, 1)
    flyout.focus_force()
    pump(root)
    reached = []
    for _ in range(18):
        focused = root.focus_get()
        focused.event_generate('<Tab>')
        pump(root)
        reached.append(root.focus_get())
    assert flyout.strength_slider in reached
    assert flyout.bright_slider in reached
    assert flyout.autostart_switch in reached
    assert flyout.toggle_btn in reached
    for _ in range(18):
        if root.focus_get() == flyout.bright_slider:
            break
        root.focus_get().event_generate('<Tab>')
        pump(root)
    assert root.focus_get() == flyout.bright_slider
    before = flyout.bright_slider.get()
    flyout.bright_slider.event_generate('<Left>')
    pump(root)
    assert flyout.bright_slider.get() == before - 1
    config.save_immediate()
    assert config.get('brightness') == (before - 1) / 100


@pytest.mark.parametrize('active,native,backend', [(False, False, True), (True, False, True), (True, True, True), (True, None, True), (True, False, False)])
def test_status_text_fits_actual_labels(window, active, native, backend):
    from nightlight_engine import engine
    root, flyout = window
    engine.is_enabled = active
    flyout.get_display_status = lambda: derive_display_status(app_enabled=active, brightness=1, windows_active=native, backend_applied=backend)
    flyout.update_ui_state()
    present(root, flyout, 1)
    for w in descendants(flyout):
        if isinstance(w, ctk.CTkLabel) and w.cget('text'):
            assert w._label.winfo_reqwidth() <= w.winfo_width(), w.cget('text')
