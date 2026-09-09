"""
System Tray Application and Socket IPC Server for Night Light by HT.
- Left-Click: Instant toggle ON/OFF with smooth fade + HUD banner confirmation
- Right-Click on Taskbar Icon: Windows JumpList (slider, direct strength levels, toggle)
- Right-Click on Tray Icon: DIRECTLY opens the Modern Adjustment Flyout with the Strength Slider!
- Localhost Socket IPC: Supports instant single-instance taskbar pinned click integration
"""

import atexit
import ctypes
from ctypes import wintypes
import hmac
import os
from pathlib import Path
import socket
import subprocess
import sys
import threading
import time
from typing import Optional

import pystray
import pystray._win32 as win32_mod
from PIL import Image
import customtkinter as ctk

from nightlight_engine import engine
from config_manager import config, get_or_create_ipc_token
from ui_flyout import ModernFlyout
from hud_overlay import HudToast
from windows_nightlight import WindowsNightLightStatus, get_windows_nightlight_status
from display_status import derive_display_status
import icons

APP_ID = "Hassan.NightLightWidget.App.1.0"

try:
    ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(APP_ID)
except Exception:
    pass

IPC_PORT = 49382


def parse_authenticated_ipc(payload: str, expected_token: str) -> Optional[str]:
    """Return the command only when the localhost payload has a valid token."""
    token, separator, command = payload.partition(" ")
    if not separator or not hmac.compare_digest(token, expected_token):
        return None
    command = command.strip()
    return command or None


class CustomTrayIcon(win32_mod.Icon):
    def __init__(self, *args, on_left_click=None, on_right_click=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.on_left_click_cb = on_left_click
        self.on_right_click_cb = on_right_click

    def _on_notify(self, wparam, lparam):
        if lparam == win32_mod.WM_LBUTTONUP:
            if self.on_left_click_cb:
                self.on_left_click_cb(self)
            else:
                self()
        elif lparam in (win32_mod.WM_RBUTTONUP, win32_mod.WM_CONTEXTMENU):
            if self.on_right_click_cb:
                self.on_right_click_cb(self)
        else:
            super()._on_notify(wparam, lparam)


class TrayApp:
    def __init__(self):
        self.root = ctk.CTk()
        self.root.withdraw()

        # Connect GUI dispatcher for 60fps animations
        engine.set_gui_dispatcher(self.root.after)

        self.flyout: Optional[ModernFlyout] = None
        self.hud: Optional[HudToast] = None
        self.tray_icon: Optional[CustomTrayIcon] = None
        self._is_running = True
        self._server_sock: Optional[socket.socket] = None
        self._ipc_token = get_or_create_ipc_token()
        self.windows_nightlight_status = WindowsNightLightStatus(None, "Checking Windows Night Light")
        if "windows_nightlight_mode" in config.data:
            config.data.pop("windows_nightlight_mode", None)
            config.save_debounced()

        # Pre-render tray icons
        self.img_active = icons.create_moon_icon(size=64, active=True)
        self.img_inactive = icons.create_moon_icon(size=64, active=False)

        # Load persisted settings into engine
        saved_enabled = config.get("enabled", False)
        saved_temp = config.get("temperature_k", 3400)
        saved_bright = config.get("brightness", 1.0)
        saved_duration = config.get("transition_duration", 0.20)

        engine.temperature_k = saved_temp
        engine.brightness = saved_bright
        engine.transition_duration = saved_duration

        # Detect Windows first so startup can never briefly double-apply warmth.
        self.windows_nightlight_status = get_windows_nightlight_status()
        engine.set_windows_nightlight_policy(
            self.windows_nightlight_status.is_enabled is not False
        )
        if saved_enabled:
            engine.set_state(enabled=True, smooth=False)

        # Initialize flyout and HUD overlay
        self.flyout = ModernFlyout(
            on_state_change=self.update_tray,
            on_quit_app=self.quit_app,
            on_windows_off=self.turn_windows_nightlight_off,
            get_display_status=self._get_display_status,
        )
        self.hud = HudToast(self.root, on_click=self.show_flyout)

        # Register Windows Taskbar JumpList
        self._ensure_jumplist()

        # Start Custom Tray Icon: Left-click = toggle, Right-click = show slider
        self.tray_icon = CustomTrayIcon(
            name="NightLightByHT",
            icon=self._get_current_image(),
            title=self._get_tooltip(),
            on_left_click=lambda icon: self._schedule_on_main(lambda: self.toggle_nightlight(show_hud=True)),
            on_right_click=lambda icon: self._schedule_on_main(self.show_flyout),
        )
        self.tray_icon.run_detached()

        # Start Localhost IPC Server
        self._start_ipc_server()
        self.root.after(2000, self._refresh_windows_nightlight_policy)

        atexit.register(self.cleanup)

    def _ensure_jumplist(self):
        """Binds taskbar shortcuts to this app, then registers its JumpList."""
        def _reg():
            try:
                base_dir = Path(sys.executable).parent if getattr(sys, "frozen", False) else Path(__file__).parent
                appid_exe = base_dir / "shortcut_appid_register.exe"
                appdata = Path(os.environ.get("APPDATA", ""))
                shortcut_names = ("Night Light by HT.lnk", "Night Light.lnk")
                shortcut_folders = (
                    appdata / "Microsoft" / "Internet Explorer" / "Quick Launch" / "User Pinned" / "TaskBar",
                    appdata / "Microsoft" / "Windows" / "Start Menu" / "Programs",
                )
                shortcuts = [folder / name for folder in shortcut_folders for name in shortcut_names]
                if appid_exe.exists():
                    for shortcut in shortcuts:
                        if shortcut.exists():
                            subprocess.run(
                                [str(appid_exe), str(shortcut), APP_ID],
                                creationflags=0x08000000,
                                timeout=10,
                            )

                jl_exe = base_dir / "wpf_jumplist.exe"
                if jl_exe.exists():
                    target_exe = base_dir / "NightLight.exe"
                    state = self._get_display_status()
                    strength = int(((6500 - engine.temperature_k) / (6500 - 1200)) * 100.0) if engine.is_enabled else 0
                    subprocess.run(
                        [str(jl_exe), str(target_exe), state.windows_label.lower(), state.hass_label.lower(), str(strength)],
                        creationflags=0x08000000,
                        timeout=10,
                    )
            except Exception:
                pass
        threading.Thread(target=_reg, daemon=True).start()

    def _get_tooltip(self) -> str:
        state = self._get_display_status()
        k = engine.temperature_k
        strength_pct = int(((6500 - k) / (6500 - 1200)) * 100.0) if engine.is_enabled else 0
        return (
            f"Windows: {state.windows_label} · HT: {state.hass_label}"
            f"\n{state.summary} · Warmth {strength_pct}%"
        )

    def _get_display_status(self):
        return derive_display_status(
            app_enabled=engine.is_enabled,
            brightness=engine.brightness,
            windows_active=self.windows_nightlight_status.is_enabled,
        )

    def _get_current_image(self) -> Image.Image:
        return self.img_active if engine.is_enabled else self.img_inactive

    def _schedule_on_main(self, callback):
        if self.root:
            self.root.after(0, callback)

    def update_tray(self):
        """Updates icon image and tooltip text."""
        if self.tray_icon:
            self.tray_icon.icon = self._get_current_image()
            self.tray_icon.title = self._get_tooltip()
        self._ensure_jumplist()

    def toggle_nightlight(self, show_hud: bool = True):
        """Toggles Night Light ON/OFF with smooth fade and HUD confirmation."""
        smooth = config.get("smooth_transitions", True)
        new_state = engine.toggle(smooth=smooth)
        config.set("enabled", new_state, save_now=True)
        self.update_tray()

        if self.flyout:
            self.flyout.update_ui_state()

        if show_hud and self.hud:
            k = engine.temperature_k
            strength_pct = int(((6500 - k) / (6500 - 1200)) * 100.0) if new_state else 0
            state = self._get_display_status()
            self.hud.show(new_state, strength_pct, k, state.hass_effective, state.detail)

    def apply_preset(self, kelvin: int):
        """Applies a specific color temperature preset."""
        if kelvin >= 6500:
            engine.set_state(temperature_k=6500, enabled=False, smooth=True)
            config.set("enabled", False, save_now=True)
        else:
            engine.set_state(temperature_k=kelvin, brightness=1.0, enabled=True, smooth=True)
            config.set("temperature_k", kelvin, save_now=True)
            config.set("brightness", 1.0, save_now=True)
            config.set("enabled", True, save_now=True)

        self.update_tray()
        if self.flyout:
            self.flyout.update_ui_state()
        if self.hud:
            strength_pct = int(((6500 - kelvin) / (6500 - 1200)) * 100.0) if kelvin < 6500 else 0
            state = self._get_display_status()
            self.hud.show(kelvin < 6500, strength_pct, kelvin, state.hass_effective, state.detail)

    def apply_strength(self, strength: int):
        """Applies a direct taskbar JumpList strength level and persists it."""
        strength = max(0, min(100, int(strength)))
        engine.set_strength_live(strength)
        config.set("temperature_k", engine.temperature_k, save_now=True)
        config.set("enabled", engine.is_enabled, save_now=True)

        self.update_tray()
        if self.flyout:
            self.flyout.update_ui_state()
        if self.hud:
            state = self._get_display_status()
            self.hud.show(
                engine.is_enabled,
                strength,
                engine.temperature_k,
                state.hass_effective,
                state.detail,
            )

    def turn_windows_nightlight_off(self):
        """Use the one-way helper that can invoke only Windows' OFF action."""
        base_dir = Path(sys.executable).parent if getattr(sys, "frozen", False) else Path(__file__).parent
        helper = base_dir / "windows_nightlight_off.exe"
        if helper.exists():
            subprocess.Popen([str(helper)], creationflags=0x08000000)
            self.root.after(2500, lambda: self._refresh_windows_nightlight_policy(schedule_next=False))

    def _refresh_windows_nightlight_policy(self, schedule_next: bool = True):
        previous = self.windows_nightlight_status.is_enabled
        self.windows_nightlight_status = get_windows_nightlight_status()
        native_blocks_ht = self.windows_nightlight_status.is_enabled is not False
        engine.set_windows_nightlight_policy(native_blocks_ht)
        if self.flyout:
            self.flyout.update_ui_state()
        if previous != self.windows_nightlight_status.is_enabled:
            self.update_tray()
        if schedule_next and self._is_running:
            self.root.after(2000, self._refresh_windows_nightlight_policy)

    def show_flyout(self):
        """Opens the modern Windows 11 adjustment flyout directly."""
        if self.flyout:
            if self.flyout.winfo_viewable():
                self.flyout.hide_flyout()
            else:
                self.flyout.show_flyout_at_tray()

    def _start_ipc_server(self):
        """Background localhost TCP socket listener for single-instance triggers."""
        def _server():
            try:
                self._server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self._server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                self._server_sock.bind(("127.0.0.1", IPC_PORT))
                self._server_sock.listen(5)
                self._server_sock.settimeout(1.0)

                while self._is_running:
                    try:
                        conn, _ = self._server_sock.accept()
                        with conn:
                            conn.settimeout(0.5)
                            payload = conn.recv(256).decode(
                                "utf-8", errors="ignore"
                            ).strip()
                            data = parse_authenticated_ipc(payload, self._ipc_token)
                            if data is None:
                                conn.sendall(b"DENIED")
                                continue

                            handled = False
                            cmd_upper = data.upper()
                            if cmd_upper == "TOGGLE":
                                self._schedule_on_main(lambda: self.toggle_nightlight(show_hud=True))
                                handled = True
                            elif cmd_upper in ("SHOW", "ADJUST", "OPEN"):
                                self._schedule_on_main(self.show_flyout)
                                handled = True
                            elif cmd_upper.startswith("PRESET"):
                                parts = data.split()
                                if len(parts) == 2 and parts[1].isdigit():
                                    k = max(1000, min(6500, int(parts[1])))
                                    self._schedule_on_main(lambda k=k: self.apply_preset(k))
                                    handled = True
                            elif cmd_upper.startswith("STRENGTH"):
                                parts = data.split()
                                if len(parts) == 2 and parts[1].isdigit():
                                    strength = max(0, min(100, int(parts[1])))
                                    self._schedule_on_main(
                                        lambda strength=strength: self.apply_strength(strength)
                                    )
                                    handled = True
                            elif cmd_upper == "WINDOWS_OFF":
                                self._schedule_on_main(self.turn_windows_nightlight_off)
                                handled = True

                            conn.sendall(b"OK" if handled else b"UNKNOWN")
                    except socket.timeout:
                        continue
                    except Exception:
                        break
            except Exception as e:
                print(f"[IPC Server] Error: {e}")

        t = threading.Thread(target=_server, daemon=True)
        t.start()

    def run(self):
        try:
            self.root.mainloop()
        except KeyboardInterrupt:
            self.quit_app()

    def quit_app(self):
        self._is_running = False
        engine.reset_to_neutral()
        self.cleanup()
        if self.root:
            try:
                self.root.quit()
                self.root.destroy()
            except Exception:
                pass
        sys.exit(0)

    def cleanup(self):
        try:
            if self.tray_icon:
                self.tray_icon.stop()
                self.tray_icon = None
            if self._server_sock:
                self._server_sock.close()
                self._server_sock = None
        except Exception:
            pass


def send_ipc_command(command: str = "TOGGLE") -> bool:
    """Sends command to running NightLight instance. Returns True if handled."""
    try:
        token = get_or_create_ipc_token()
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as client:
            client.settimeout(0.5)
            client.connect(("127.0.0.1", IPC_PORT))
            client.sendall(f"{token} {command}".encode("utf-8"))
            return client.recv(16) == b"OK"
    except Exception:
        return False
