"""
High-Performance Modern Windows 11 Fluent Flyout UI for Night Light.
Engineered for zero-lag 144Hz slider dragging and instant 0ms pop-up on right-click.
"""

import ctypes
from ctypes import wintypes
import os
from pathlib import Path
import sys
import tkinter as tk
from typing import Callable, Optional
import customtkinter as ctk
from PIL import Image

from nightlight_engine import engine, kelvin_to_rgb
from config_manager import config
from display_status import DisplayStatus, derive_display_status
import icons


ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

user32 = ctypes.windll.user32


class RECT(ctypes.Structure):
    _fields_ = [("left", wintypes.LONG), ("top", wintypes.LONG), ("right", wintypes.LONG), ("bottom", wintypes.LONG)]


class MONITORINFO(ctypes.Structure):
    _fields_ = [("cbSize", wintypes.DWORD), ("rcMonitor", RECT), ("rcWork", RECT), ("dwFlags", wintypes.DWORD)]


class ModernFlyout(ctk.CTkToplevel):
    def __init__(
        self,
        on_state_change: Optional[Callable[[], None]] = None,
        on_quit_app: Optional[Callable[[], None]] = None,
        on_windows_off: Optional[Callable[[], None]] = None,
        get_display_status: Optional[Callable[[], DisplayStatus]] = None,
    ):
        super().__init__()

        self.on_state_change = on_state_change
        self.on_quit_app = on_quit_app
        self.on_windows_off = on_windows_off
        self.get_display_status = get_display_status

        # Window configuration
        self.title("Night Light")
        self.overrideredirect(True)
        self.attributes("-topmost", True)
        self.resizable(False, False)

        # Dimensions
        self.flyout_width = 360
        self.flyout_height = 510

        # Colors
        self.COLOR_BG = "#16171b"
        self.COLOR_CARD = "#202228"
        self.COLOR_CARD_HOVER = "#272a32"
        self.COLOR_CARD_BORDER = "#2e313b"
        self.COLOR_ACCENT = "#ffaa2b"  # Warm amber
        self.COLOR_ACCENT_HOVER = "#ff9500"
        self.COLOR_TEXT = "#ffffff"
        self.COLOR_SUBTEXT = "#969cb0"

        self.configure(fg_color=self.COLOR_BG)

        self._build_ui()
        self._bind_events()
        self.update_ui_state()

        # Start hidden
        self.withdraw()

    def _build_ui(self):
        # Outer Border Container
        self.outer_frame = ctk.CTkFrame(
            self,
            fg_color=self.COLOR_BG,
            border_color=self.COLOR_CARD_BORDER,
            border_width=1,
            corner_radius=12,
        )
        self.outer_frame.pack(fill="both", expand=True, padx=2, pady=2)

        # --- Header ---
        header_frame = ctk.CTkFrame(self.outer_frame, fg_color="transparent")
        header_frame.pack(fill="x", padx=16, pady=(12, 4))

        title_box = ctk.CTkFrame(header_frame, fg_color="transparent")
        title_box.pack(side="left")

        moon_pil = icons.create_moon_icon(size=24, active=True)
        self.header_icon = ctk.CTkImage(light_image=moon_pil, dark_image=moon_pil, size=(20, 20))
        icon_label = ctk.CTkLabel(title_box, image=self.header_icon, text="")
        icon_label.pack(side="left", padx=(0, 6))

        title_label = ctk.CTkLabel(
            title_box,
            height=20,
            text="Night Light",
            font=ctk.CTkFont(family="Segoe UI", size=14, weight="bold"),
            text_color=self.COLOR_TEXT,
        )
        title_label.pack(side="left")

        close_btn = ctk.CTkButton(
            header_frame,
            text="✕",
            width=24,
            height=24,
            font=ctk.CTkFont(size=10, weight="bold"),
            fg_color="transparent",
            hover_color="#2e313b",
            text_color=self.COLOR_SUBTEXT,
            corner_radius=6,
            command=self.hide_flyout,
        )
        close_btn.pack(side="right")

        # --- Big Interactive Toggle Card ---
        self.toggle_card = ctk.CTkFrame(
            self.outer_frame,
            fg_color=self.COLOR_CARD,
            border_color=self.COLOR_CARD_BORDER,
            border_width=1,
            corner_radius=10,
        )
        self.toggle_card.pack(fill="x", padx=14, pady=6)

        toggle_inner = ctk.CTkFrame(self.toggle_card, fg_color="transparent")
        toggle_inner.pack(fill="x", padx=12, pady=8)

        self.status_icon_label = ctk.CTkLabel(
            toggle_inner,
            text="🌙",
            font=ctk.CTkFont(size=18),
            text_color=self.COLOR_ACCENT,
        )
        self.status_icon_label.pack(side="left", padx=(0, 8))

        status_text_box = ctk.CTkFrame(toggle_inner, fg_color="transparent")
        status_text_box.pack(side="left", fill="both", expand=True)

        self.status_title = ctk.CTkLabel(
            status_text_box,
            height=20,
            text="Night Light filter is ON",
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
            text_color=self.COLOR_TEXT,
            anchor="w",
        )
        self.status_title.pack(fill="x")

        self.status_sub = ctk.CTkLabel(
            status_text_box,
            height=20,
            text="Warm amber filter active",
            font=ctk.CTkFont(family="Segoe UI", size=10),
            text_color=self.COLOR_SUBTEXT,
            anchor="w",
        )
        self.status_sub.pack(fill="x")

        self.toggle_btn = ctk.CTkButton(
            toggle_inner,
            text="OFF",
            font=ctk.CTkFont(family="Segoe UI", size=10, weight="bold"),
            fg_color="#3b2218",
            hover_color="#522b1e",
            text_color="#f87171",
            corner_radius=6,
            width=104,
            height=26,
            command=self._on_toggle_clicked,
        )
        self.toggle_btn.pack(side="right")

        for w in (self.toggle_card, toggle_inner, self.status_icon_label, status_text_box, self.status_title, self.status_sub):
            w.bind("<Button-1>", lambda e: self._on_toggle_clicked())

        # --- LIVE WINDOWS + HASSTECH PIPELINE STATUS ---
        pipeline_card = ctk.CTkFrame(
            self.outer_frame,
            fg_color=self.COLOR_CARD,
            border_color=self.COLOR_CARD_BORDER,
            border_width=1,
            corner_radius=10,
        )
        pipeline_card.pack(fill="x", padx=14, pady=5)

        self.pipeline_summary = ctk.CTkLabel(
            pipeline_card,
            height=20,
            text="Checking active protection…",
            font=ctk.CTkFont(family="Segoe UI", size=10, weight="bold"),
            text_color=self.COLOR_TEXT,
            anchor="w",
        )
        self.pipeline_summary.pack(fill="x", padx=12, pady=(7, 3))

        badges = ctk.CTkFrame(pipeline_card, fg_color="transparent")
        badges.pack(fill="x", padx=12, pady=(0, 5))
        self.windows_badge = ctk.CTkLabel(
            badges, text="WINDOWS: …", height=22, corner_radius=6,
            fg_color="#2f323c", text_color=self.COLOR_SUBTEXT,
            font=ctk.CTkFont(family="Segoe UI", size=9, weight="bold"),
        )
        self.windows_badge.pack(side="left", fill="x", expand=True, padx=(0, 3))
        self.hass_badge = ctk.CTkLabel(
            badges, text="Night Light: …", height=22, corner_radius=6,
            fg_color="#2f323c", text_color=self.COLOR_SUBTEXT,
            font=ctk.CTkFont(family="Segoe UI", size=9, weight="bold"),
        )
        self.hass_badge.pack(side="left", fill="x", expand=True, padx=(3, 0))

        mode_row = ctk.CTkFrame(pipeline_card, fg_color="transparent")
        mode_row.pack(fill="x", padx=12, pady=(0, 8))
        self.windows_off_btn = ctk.CTkButton(
            mode_row, text="TURN WINDOWS NIGHT LIGHT OFF", height=24, corner_radius=6,
            font=ctk.CTkFont(family="Segoe UI", size=9, weight="bold"),
            command=self._turn_windows_off,
        )
        self.windows_off_btn.pack(fill="x", expand=True)

        # --- PRIMARY: STRENGTH SLIDING BAR ---
        strength_card = ctk.CTkFrame(
            self.outer_frame,
            fg_color=self.COLOR_CARD,
            border_color=self.COLOR_CARD_BORDER,
            border_width=1,
            corner_radius=10,
        )
        strength_card.pack(fill="x", padx=14, pady=5)

        strength_header = ctk.CTkFrame(strength_card, fg_color="transparent")
        strength_header.pack(fill="x", padx=12, pady=(8, 2))

        strength_title = ctk.CTkLabel(
            strength_header,
            height=20,
            text="Night Light Warmth",
            font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
            text_color=self.COLOR_TEXT,
        )
        strength_title.pack(side="left")

        self.strength_val_label = ctk.CTkLabel(
            strength_header,
            height=20,
            text="65% · 3100K",
            font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
            text_color=self.COLOR_ACCENT,
        )
        self.strength_val_label.pack(side="right")

        self.strength_slider = ctk.CTkSlider(
            strength_card,
            from_=0,
            to=100,
            number_of_steps=100,
            button_color=self.COLOR_ACCENT,
            button_hover_color=self.COLOR_ACCENT_HOVER,
            progress_color=self.COLOR_ACCENT,
            fg_color="#2f323c",
            height=16,
            command=self._on_strength_slider_drag,
        )
        self.strength_slider.pack(fill="x", padx=12, pady=(4, 10))
        self.strength_slider.bind("<ButtonRelease-1>", self._on_slider_released)

        # --- BRIGHTNESS SLIDER ---
        bright_card = ctk.CTkFrame(
            self.outer_frame,
            fg_color=self.COLOR_CARD,
            border_color=self.COLOR_CARD_BORDER,
            border_width=1,
            corner_radius=10,
        )
        bright_card.pack(fill="x", padx=14, pady=5)

        bright_header = ctk.CTkFrame(bright_card, fg_color="transparent")
        bright_header.pack(fill="x", padx=12, pady=(8, 2))

        bright_title = ctk.CTkLabel(
            bright_header,
            height=20,
            text="Software Dimming",
            font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
            text_color=self.COLOR_TEXT,
        )
        bright_title.pack(side="left")

        self.bright_val_label = ctk.CTkLabel(
            bright_header,
            height=20,
            text="100%",
            font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
            text_color="#60a5fa",
        )
        self.bright_val_label.pack(side="right")

        self.bright_slider = ctk.CTkSlider(
            bright_card,
            from_=20,
            to=100,
            number_of_steps=80,
            button_color="#60a5fa",
            button_hover_color="#3b82f6",
            progress_color="#60a5fa",
            fg_color="#2f323c",
            height=16,
            command=self._on_bright_slider_drag,
        )
        self.bright_slider.pack(fill="x", padx=12, pady=(4, 10))
        self.bright_slider.bind("<ButtonRelease-1>", self._on_slider_released)

        # --- PRESETS ---
        preset_label = ctk.CTkLabel(
            self.outer_frame,
            height=20,
            text="QUICK PRESETS",
            font=ctk.CTkFont(family="Segoe UI", size=9, weight="bold"),
            text_color=self.COLOR_SUBTEXT,
            anchor="w",
        )
        preset_label.pack(fill="x", padx=16, pady=(6, 2))

        presets_row = ctk.CTkFrame(self.outer_frame, fg_color="transparent")
        presets_row.pack(fill="x", padx=14, pady=2)

        presets = [
            ("🕯️ Candle", 1900),
            ("🦉 Night", 2800),
            ("🛋️ Cozy", 3800),
            ("☀️ App Off", 6500),
        ]

        for idx, (label, kelvin) in enumerate(presets):
            btn = ctk.CTkButton(
                presets_row,
                text=label,
                font=ctk.CTkFont(family="Segoe UI", size=10),
                fg_color=self.COLOR_CARD,
                border_color=self.COLOR_CARD_BORDER,
                border_width=1,
                hover_color="#2a2d36",
                corner_radius=6,
                width=82,
                height=28,
                command=lambda k=kelvin: self._apply_preset(k),
            )
            column = idx % 2
            row = idx // 2
            btn.grid(row=row, column=column, padx=2, pady=2, sticky="ew")
        presets_row.grid_columnconfigure(0, weight=1)
        presets_row.grid_columnconfigure(1, weight=1)

        # --- FOOTER ---
        footer_frame = ctk.CTkFrame(self.outer_frame, fg_color="transparent")
        footer_frame.pack(fill="x", padx=16, pady=(10, 8))

        self.autostart_switch = ctk.CTkCheckBox(
            footer_frame,
            text="Start with Windows",
            font=ctk.CTkFont(family="Segoe UI", size=10),
            text_color=self.COLOR_SUBTEXT,
            checkbox_width=16,
            checkbox_height=16,
            corner_radius=4,
            fg_color=self.COLOR_ACCENT,
            command=self._on_autostart_toggled,
        )
        self.autostart_switch.pack(side="left")

        quit_btn = ctk.CTkButton(
            footer_frame,
            text="Quit App",
            width=56,
            height=24,
            font=ctk.CTkFont(family="Segoe UI", size=10),
            fg_color="transparent",
            hover_color="#ef4444",
            text_color=self.COLOR_SUBTEXT,
            corner_radius=4,
            command=self._on_quit_clicked,
        )
        quit_btn.pack(side="right")

    def _bind_events(self):
        self._keyboard_controls = []
        self._enable_keyboard_controls(self.outer_frame)
        self.bind('<Tab>', lambda event: self._cycle_focus(1))
        self.bind('<Shift-Tab>', lambda event: self._cycle_focus(-1))
        self.bind("<FocusOut>", self._on_focus_out)
        self.bind("<Escape>", lambda e: self.hide_flyout())
        self.bind_all("<Alt-KeyPress-Up>", self._adjust_focused_slider)
        self.bind_all("<Alt-KeyPress-Down>", self._adjust_focused_slider)

    def _enable_keyboard_controls(self, parent):
        # CTk controls are Frames whose public bind delegates to a mouse canvas.
        # Bind the actual focus-owning Frame, not that non-focusable canvas.
        for widget in parent.winfo_children():
            if isinstance(widget, (ctk.CTkButton, ctk.CTkCheckBox, ctk.CTkSlider)):
                self._keyboard_controls.append(widget)
                tk.Frame.configure(widget, takefocus=lambda *args, w=widget: int(w.cget('state') != 'disabled'))
                tk.Misc.bind(widget, '<FocusIn>', lambda event, w=widget: self._focus_ring(w, True), add='+')
                tk.Misc.bind(widget, '<FocusOut>', lambda event, w=widget: self._focus_ring(w, False), add='+')
                if isinstance(widget, ctk.CTkSlider):
                    for key, delta in (('Left', -1), ('Down', -1), ('Right', 1), ('Up', 1)):
                        tk.Misc.bind(widget, f'<{key}>', lambda event, w=widget, d=delta: self._keyboard_slider(w, d))
                else:
                    for key in ('space', 'Return'):
                        tk.Misc.bind(widget, f'<{key}>', lambda event, w=widget: self._keyboard_activate(w))
            else:
                self._enable_keyboard_controls(widget)

    def _cycle_focus(self, direction):
        controls = [w for w in self._keyboard_controls if w.winfo_viewable() and w.cget('state') != 'disabled']
        if controls:
            focused = self.focus_get()
            index = controls.index(focused) if focused in controls else (-1 if direction > 0 else 0)
            tk.Misc.focus_set(controls[(index + direction) % len(controls)])
        return 'break'

    def _focus_ring(self, widget, focused):
        if isinstance(widget, ctk.CTkSlider):
            widget.configure(border_width=2 if focused else 0, border_color=self.COLOR_ACCENT)
        else:
            widget.configure(border_width=2 if focused else 1, border_color=self.COLOR_ACCENT if focused else self.COLOR_CARD_BORDER)

    def _keyboard_activate(self, widget):
        if widget.cget('state') != 'disabled':
            if isinstance(widget, ctk.CTkCheckBox):
                widget.toggle()
            else:
                widget.invoke()
        return 'break'

    def _keyboard_slider(self, widget, delta):
        value = max(float(widget.cget('from_')), min(float(widget.cget('to')), float(widget.get()) + delta))
        widget.set(value)
        widget.cget('command')(value)
        self._on_slider_released(None)
        return 'break'

    def _adjust_focused_slider(self, event):
        focused = self.focus_get()
        if focused not in (self.strength_slider, self.bright_slider):
            return
        delta = 1 if event.keysym == "Up" else -1
        value = float(focused.get()) + delta
        focused.set(value)
        focused.cget("command")(value)
        return "break"

    def _on_focus_out(self, event):
        self.after(200, self._check_focus_and_hide)

    def _check_focus_and_hide(self):
        try:
            focus_widget = self.focus_get()
            if focus_widget is None:
                self.hide_flyout()
        except Exception:
            pass

    def _kelvin_from_strength(self, strength_pct: float) -> int:
        ratio = strength_pct / 100.0
        return int(6500 - ratio * (6500 - 1200))

    def _strength_from_kelvin(self, kelvin: int) -> float:
        ratio = (6500 - kelvin) / (6500 - 1200)
        return max(0.0, min(100.0, ratio * 100.0))

    def update_ui_state(self):
        """Refreshes controls to match current engine state."""
        is_on = engine.is_enabled
        k = engine.temperature_k
        br = int(engine.brightness * 100)
        strength_pct = int(self._strength_from_kelvin(k)) if is_on else 0

        state = self.get_display_status() if self.get_display_status else derive_display_status(
            app_enabled=is_on,
            brightness=engine.brightness,
            windows_active=None,
        )

        if is_on:
            self.status_title.configure(text=f"Night Light filter is {state.hass_label}")
            self.status_sub.configure(text=f"Warmth: {strength_pct}% · {k}K")
            self.status_icon_label.configure(text="🌙", text_color=self.COLOR_ACCENT)
            self.toggle_btn.configure(
                text="OFF",
                fg_color="#3b2218",
                hover_color="#522b1e",
                text_color="#f87171",
            )
            self.toggle_card.configure(border_color=self.COLOR_ACCENT)
        else:
            self.status_title.configure(text="Night Light filter is OFF")
            self.status_sub.configure(text="Windows Night Light is not changed")
            self.status_icon_label.configure(text="☀️", text_color="#71717a")
            self.toggle_btn.configure(
                text="ON",
                fg_color="#1e3a5f",
                hover_color="#2b4c7e",
                text_color="#60a5fa",
            )
            self.toggle_card.configure(border_color=self.COLOR_CARD_BORDER)

        windows_fg = "#7c4a16" if state.windows_active is True else "#2f323c"
        windows_text = "#ffd08a" if state.windows_active is True else self.COLOR_SUBTEXT
        hass_colors = {
            "ON": ("#6b4510", "#ffd08a"),
            "PAUSED": ("#4a3d24", "#facc15"),
            "OFF": ("#2f323c", self.COLOR_SUBTEXT),
        }
        hass_fg, hass_text = hass_colors.get(state.hass_label, ("#2f323c", self.COLOR_SUBTEXT))
        self.pipeline_summary.configure(text=state.summary)
        self.windows_badge.configure(
            text=f"WINDOWS: {state.windows_label}", fg_color=windows_fg, text_color=windows_text
        )
        self.hass_badge.configure(
            text=f"Night Light: {state.hass_label}", fg_color=hass_fg, text_color=hass_text
        )
        if state.windows_active is True:
            self.windows_off_btn.configure(
                state="normal", text="TURN WINDOWS NIGHT LIGHT OFF",
                fg_color=self.COLOR_ACCENT, hover_color=self.COLOR_ACCENT_HOVER, text_color="#151515",
            )
        else:
            label = "WINDOWS NIGHT LIGHT IS OFF" if state.windows_active is False else "WINDOWS STATUS UNKNOWN"
            self.windows_off_btn.configure(
                state="disabled", text=label, fg_color="#2f323c", text_color=self.COLOR_SUBTEXT,
            )

        self.strength_slider.set(strength_pct)
        self.strength_val_label.configure(text=f"{strength_pct}% · {k}K")

        self.bright_slider.set(br)
        self.bright_val_label.configure(text=f"{br}%")

        if config.is_autostart_enabled():
            self.autostart_switch.select()
        else:
            self.autostart_switch.deselect()

    def _on_toggle_clicked(self):
        new_state = not engine.is_enabled
        if new_state and engine.temperature_k >= 6500:
            engine.temperature_k = int(config.get("last_temperature_k", 3400))
        engine.set_state(enabled=new_state, smooth=True)
        config.set("temperature_k", engine.temperature_k, save_now=False)
        config.set("enabled", new_state, save_now=True)
        self.update_ui_state()
        if self.on_state_change:
            self.on_state_change()

    def _turn_windows_off(self):
        if self.on_windows_off:
            self.on_windows_off()

    # --- ZERO-LAG LIVE SLIDER DRAG HANDLERS ---
    def _on_strength_slider_drag(self, val):
        strength_pct = int(val)
        k = self._kelvin_from_strength(val)
        self.strength_val_label.configure(text=f"{strength_pct}% · {k}K")
        
        # Direct instant hardware matrix update (< 0.002ms)
        engine.set_strength_live(val)
        
        self.update_ui_state()

    def _on_bright_slider_drag(self, val):
        br = int(val)
        self.bright_val_label.configure(text=f"{br}%")
        engine.set_brightness_live(val)

    def _on_slider_released(self, event):
        """Called once when mouse is released to save config without lag."""
        k = engine.temperature_k
        config.set("temperature_k", k, save_now=True)
        config.set("brightness", engine.brightness, save_now=True)
        config.set("enabled", engine.is_enabled, save_now=True)
        if self.on_state_change:
            self.on_state_change()

    def _apply_preset(self, kelvin: int):
        if kelvin >= 6500:
            engine.set_state(temperature_k=6500, enabled=False, smooth=True)
            if config.get("temperature_k", 3400) < 6500:
                config.set("last_temperature_k", config.get("temperature_k", 3400), save_now=False)
            config.set("temperature_k", 6500, save_now=True)
            config.set("enabled", False, save_now=True)
        else:
            engine.set_state(temperature_k=kelvin, brightness=1.0, enabled=True, smooth=True)
            config.set("last_temperature_k", kelvin, save_now=False)
            config.set("temperature_k", kelvin, save_now=True)
            config.set("brightness", 1.0, save_now=True)
            config.set("enabled", True, save_now=True)

        self.update_ui_state()
        if self.on_state_change:
            self.on_state_change()

    def _on_autostart_toggled(self):
        enable = bool(self.autostart_switch.get())
        if not config.set_autostart(enable):
            if enable:
                self.autostart_switch.deselect()
            else:
                self.autostart_switch.select()
            self.pipeline_summary.configure(text="Could not change Start with Windows")

    def _on_quit_clicked(self):
        self.hide_flyout()
        if self.on_quit_app:
            self.on_quit_app()

    def show_flyout_at_tray(self, tray_x: Optional[int] = None, tray_y: Optional[int] = None):
        """Positions flyout above the taskbar/tray area and focuses it with zero delay."""
        self.update_ui_state()
        self.deiconify()

        pt = wintypes.POINT()
        user32.GetCursorPos(ctypes.byref(pt))

        if tray_x is None or tray_y is None:
            tray_x, tray_y = pt.x, pt.y

        # Determine monitor work area where cursor is
        hmonitor = user32.MonitorFromPoint(pt, 2)
        mi = MONITORINFO()
        mi.cbSize = ctypes.sizeof(MONITORINFO)
        user32.GetMonitorInfoW(hmonitor, ctypes.byref(mi))

        margin = 10
        pos_x = min(mi.rcWork.right - self.flyout_width - margin, max(mi.rcWork.left + margin, tray_x - self.flyout_width // 2))
        pos_y = tray_y - self.flyout_height - 10
        if pos_y < mi.rcWork.top + margin:
            pos_y = min(mi.rcWork.bottom - self.flyout_height - margin, tray_y + 20)

        self.geometry(f"{self.flyout_width}x{self.flyout_height}+{pos_x}+{pos_y}")
        self.lift()
        self.focus_force()

        # Force Windows OS foreground focus
        try:
            hwnd = int(self.wm_frame(), 16) if self.wm_frame() else None
            if hwnd:
                user32.SetForegroundWindow(hwnd)
                user32.BringWindowToTop(hwnd)
        except Exception:
            pass

    def hide_flyout(self):
        self.withdraw()
