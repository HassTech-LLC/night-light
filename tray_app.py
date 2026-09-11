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
import hashlib
import os
from pathlib import Path
import socket
import subprocess
import sys
import threading
import time
from typing import Optional

from PIL import Image
import customtkinter as ctk

from win32_tray import TrayIcon

from nightlight_engine import engine
from config_manager import config, get_or_create_ipc_token
from ipc_transport import authenticate_request, acknowledge, send_ipc_command
from premium_ui import PremiumFlyout
from hud_overlay import HudToast
from windows_nightlight import WindowsNightLightStatus, get_windows_nightlight_status
from display_status import derive_display_status
from smart_mode import SmartController
from smart_desktop import SmartDesktopController, is_v2_controller
from smart_migration import uses_v2, initialize_first_install
from smart_migration_switch import MigrationSwitch
from smart_ui import show_smart_setup
from smart_windows import EmergencyHotkey, idle_seconds, high_contrast_active
from datetime import datetime
import icons

APP_ID = "Hassan.NightLightWidget.App.1.0"

IPC_PORT = 49382


def parse_authenticated_ipc(payload: str, expected_token: str) -> Optional[str]:
    """Return the command only when the localhost payload has a valid token."""
    if not isinstance(payload, str) or not isinstance(expected_token, str):
        return None
    token, separator, command = payload.partition(" ")
    if not separator or not token.isascii() or not expected_token.isascii():
        return None
    if not hmac.compare_digest(token, expected_token):
        return None
    command = command.strip()
    return command or None


def ipc_ack(command: str, token: str) -> bytes:
    """Create a server proof bound to the authenticated command."""
    digest = hmac.new(token.encode("ascii"), command.encode("utf-8"), hashlib.sha256).hexdigest()[:32]
    return f"OK:{digest}".encode("ascii")


class TrayApp:
    def __init__(self, listener):
        try:
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(APP_ID)
        except Exception:
            pass
        self.root = ctk.CTk()
        self.root.withdraw()

        # Connect GUI dispatcher for 60fps animations
        engine.set_gui_dispatcher(self.root.after)

        self.flyout: Optional[PremiumFlyout] = None
        self.hud: Optional[HudToast] = None
        self.tray_icon: Optional[TrayIcon] = None
        self._is_running = True
        self._server_sock: Optional[socket.socket] = listener
        self._ipc_token = get_or_create_ipc_token()
        self._clean_exit_requested = False
        initialize_first_install(config)
        config.begin_session()
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
        try:
            restore_hold = time.time() < float(config.get('smart_hold_until',0)) <= time.time()+3600 and config.get('smart_hold_kind') != 'pause'
        except (ValueError, TypeError):
            restore_hold = False
        if not uses_v2(config) and saved_enabled and (not config.get('smart_enabled', False) or restore_hold):
            engine.set_state(enabled=True, smooth=False)

        self.smart = SmartDesktopController(engine, config) if uses_v2(config) else SmartController(engine, config)
        self.smart_window = None
        self.emergency_hotkey=EmergencyHotkey(self._emergency_reset)
        self.smart.hotkey_status='Ctrl+Shift+N ready' if self.emergency_hotkey.active else 'Ctrl+Shift+N unavailable — use App Off'
        self.root.after(100,self._poll_emergency)

        # Initialize flyout and HUD overlay
        self.flyout = PremiumFlyout(self, engine, config)
        self.hud = HudToast(self.root, on_click=self.show_flyout)

        # Register Windows Taskbar JumpList
        self._ensure_jumplist()

        # Start Custom Tray Icon: Left-click = toggle, Right-click = show slider
        self.tray_icon = TrayIcon(
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
        self._smart_timer=self.root.after(100, self._tick_smart)

        atexit.register(self.cleanup)

    def migration_interlocked(self):
        switch=getattr(self,'_migration',None)
        return switch is not None and (not switch.done or
            switch.result.get('outcome') in {'migration_off_not_saved','migration_activation_failed'} or
            (uses_v2(config) and not switch.result.get('adopted',False)))

    def migration_off(self):
        switch=getattr(self,'_migration',None)
        if switch is not None and not switch.done:switch.off()
        else:engine.reset_to_neutral()
        return 'Off requested. Finishing the settings handoff; display reset is not yet confirmed.'

    def begin_smart_migration(self,proposal,binary_path):
        """Native-only entry; caller must supply installer-verified prior binary.

        No web command accepts a binary path or can manufacture a proposal.
        The public review remains disabled until installer/rollback is ready.
        """
        if self.migration_interlocked() or uses_v2(config):
            raise ValueError('A migration is already active or complete.')
        if config.automatic_output_blocked or not config.session_id:
            raise ValueError('Recovery storage is unavailable. Restart before switching.')
        if self.smart_window is not None and self.smart_window.winfo_exists():
            raise ValueError('Close the older schedule editor before switching.')
        if isinstance(self.flyout,PremiumFlyout):
            self.flyout.actions.preview=None
            self.flyout.actions.preview_deadline=0
        def adopt():
            previous=self.smart
            self.smart=SmartDesktopController(engine,config)
            self.smart.hotkey_status=previous.hotkey_status
        self._migration=MigrationSwitch(config,engine,proposal,binary_path,adopt)
        timer=getattr(self,'_smart_timer',None)
        if timer is not None:self.root.after_cancel(timer)
        self._smart_timer=self.root.after(100,self._tick_smart)

    def _ensure_jumplist(self):
        """Binds taskbar shortcuts to this app, then registers its JumpList."""
        state = self._get_display_status()
        try:held = float(config.get('smart_hold_until',0))>time.time()
        except (ValueError,TypeError):held=False
        if is_v2_controller(self.smart):held=self.smart.owner.state.override is not None
        smart_state = ('paused' if held else 'active') if self.smart.enabled else 'off'
        signature = (state.windows_label.lower(), smart_state)
        if getattr(self,'_jumplist_signature',None)==signature or getattr(self,'_jumplist_busy',False):return
        self._jumplist_busy=True
        def _reg():
            try:
                base_dir = Path(sys.executable).parent if getattr(sys, "frozen", False) else Path(__file__).parent
                appid_exe = base_dir / "shortcut_appid_register.exe"
                appdata = Path(os.environ.get("APPDATA", ""))
                shortcut_names = ("Night Light by HT.lnk", "Night Light.lnk", "Night Light Controls.lnk")
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
                    subprocess.run(
                        [str(jl_exe), str(target_exe), signature[0], signature[1]],
                        creationflags=0x08000000,
                        timeout=10,
                        check=True,
                    )
                    self._jumplist_signature=signature
            except Exception:
                pass
            finally:self._jumplist_busy=False
        threading.Thread(target=_reg, daemon=True).start()

    def taskbar_smart(self, pause):
        if self.migration_interlocked():return
        """Explicit shortcuts; a stale pause cannot toggle the filter back on."""
        if self.smart.enabled:
            if getattr(getattr(self,'flyout',None),'actions',None):self.flyout.actions.end_preview()
            if pause:self.smart.hold(pause=True)
            else:self.smart.resume()
            self.update_tray()
            if self.flyout:self.flyout.update_ui_state()
        else:self.show_flyout()

    def show_smart_setup(self):
        if self.migration_interlocked():
            self.show_flyout();return
        if is_v2_controller(self.smart):
            self.show_flyout()
            return
        if self.smart_window is not None and self.smart_window.winfo_exists():
            self.smart_window.lift()
            return
        self.smart_window = show_smart_setup(self.root, self.smart)

    def _tick_smart(self):
        if not self._is_running:
            return
        if self.migration_interlocked():
            self._migration.poll()
            if self.flyout:self.flyout.update_ui_state()
            self._smart_timer=self.root.after(100,self._tick_smart)
            return
        if is_v2_controller(self.smart):
            try:
                now=time.monotonic()
                if now>=getattr(self,'_v2_ui_due',0):
                    self._v2_ui_due=now+1
                    if self.smart.enabled and high_contrast_active():
                        self.smart.manual(reset=True)
                        self.smart.status='Smart stopped for Windows high contrast'
                    self.update_tray()
                    if self.flyout:self.flyout.update_ui_state()
                self.smart.tick()
            finally:
                if self._is_running:self._smart_timer=self.root.after(100,self._tick_smart)
            return
        try:
            self.smart.learner.observe(datetime.now().astimezone(),idle_seconds())
            if self.smart.enabled and high_contrast_active():
                if isinstance(self.flyout, PremiumFlyout):self.flyout.actions.preview=None
                self.smart.manual(reset=True)
                self.smart.status='Smart stopped for Windows high contrast — re-enable after turning high contrast off'
            elif not (isinstance(self.flyout, PremiumFlyout) and self.flyout.actions.preview):
                self.smart.tick()
            self._ensure_jumplist()
            if self.flyout:
                self.flyout.update_ui_state()
            if self.tray_icon:
                self.tray_icon.icon = self._get_current_image()
                self.tray_icon.title = self._get_tooltip()
        finally:
            if self._is_running:
                self._smart_timer=self.root.after(25000, self._tick_smart)

    def _poll_emergency(self):
        if not self._is_running:return
        self.emergency_hotkey.poll()
        self.root.after(100,self._poll_emergency)

    def _emergency_reset(self):
        if self.migration_interlocked():
            self.migration_off();return
        if isinstance(self.flyout, PremiumFlyout):self.flyout.actions.preview=None
        self.smart.manual(reset=True)
        if self.flyout:self.flyout.update_ui_state()
        self.update_tray()

    def _get_tooltip(self) -> str:
        state = self._get_display_status()
        k = engine.temperature_k
        strength_pct = int(((6500 - k) / (6500 - 1200)) * 100.0) if engine.is_enabled else 0
        return (
            f"Windows Night Light: {state.windows_label} · Night Light: {state.hass_label}"
            f"\n{state.summary} · Warmth {strength_pct}%"
        )

    def _get_display_status(self):
        return derive_display_status(
            app_enabled=engine.is_enabled,
            brightness=engine.brightness,
            windows_active=self.windows_nightlight_status.is_enabled,
            backend_applied=engine.is_applied,
            output_fault=engine.output_fault,
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
        if self.migration_interlocked():
            self.migration_off();return
        if is_v2_controller(getattr(self,'smart',None)):
            self.smart.toggle();self.update_tray()
            if self.flyout:self.flyout.update_ui_state()
            return
        if getattr(getattr(self,'flyout',None),'actions',None):self.flyout.actions.end_preview()
        if getattr(self, 'smart', None):
            self.smart.hold()
        smooth = config.get("smooth_transitions", True)
        if not engine.is_enabled and engine.temperature_k >= 6500:
            engine.temperature_k = int(config.get("last_temperature_k", 3400))
        new_state = engine.toggle(smooth=smooth)
        config.set("temperature_k", engine.temperature_k, save_now=False)
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
        if self.migration_interlocked():
            if kelvin>=6500:self.migration_off()
            return
        if is_v2_controller(getattr(self,'smart',None)):
            if kelvin>=6500:self.smart.command('off')
            else:self.smart.adjust(kelvin)
            self.update_tray()
            if self.flyout:self.flyout.update_ui_state()
            return
        if getattr(getattr(self,'flyout',None),'actions',None):self.flyout.actions.end_preview()
        if getattr(self, 'smart', None):
            self.smart.manual(reset=True) if kelvin >= 6500 else self.smart.hold()
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

        self.update_tray()
        if self.flyout:
            self.flyout.update_ui_state()
        if self.hud:
            strength_pct = int(((6500 - kelvin) / (6500 - 1200)) * 100.0) if kelvin < 6500 else 0
            state = self._get_display_status()
            self.hud.show(kelvin < 6500, strength_pct, kelvin, state.hass_effective, state.detail)

    def apply_strength(self, strength: int):
        """Applies a direct taskbar JumpList strength level and persists it."""
        if self.migration_interlocked():
            if strength==0:self.migration_off()
            return
        if is_v2_controller(getattr(self,'smart',None)):
            strength=max(0,min(100,int(strength)))
            self.apply_preset(round(6500-5300*strength/100))
            return
        if getattr(getattr(self,'flyout',None),'actions',None):self.flyout.actions.end_preview()
        strength = max(0, min(100, int(strength)))
        if getattr(self, 'smart', None):
            self.smart.manual(reset=True) if strength == 0 else self.smart.hold()
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
        engine.refresh_output_observation()
        previous = self.windows_nightlight_status.is_enabled
        self.windows_nightlight_status = get_windows_nightlight_status()
        native_blocks_ht = self.windows_nightlight_status.is_enabled is not False
        if self.migration_interlocked():
            engine.set_windows_nightlight_policy(native_blocks_ht)
        elif is_v2_controller(getattr(self,'smart',None)):
            engine.set_windows_nightlight_policy(native_blocks_ht)
            self.smart.tick()
        elif getattr(self, 'smart', None) and self.smart.enabled and not native_blocks_ht and engine.is_suppressed_by_windows_nightlight:
            # Clear policy while neutral, then let Smart fade to its current curve.
            was_enabled = engine.is_enabled
            engine.set_state(enabled=False, smooth=False)
            engine.set_windows_nightlight_policy(False)
            try:
                hold_active = time.time() < float(config.get('smart_hold_until',0)) <= time.time()+3600
            except (TypeError,ValueError):
                hold_active = False
            if hold_active and config.get('smart_hold_kind') != 'pause':
                engine.set_state(enabled=was_enabled, smooth=True, duration=120)
            self.smart.rejoin = True
            self.smart.fade_until = 0
            if not (isinstance(self.flyout, PremiumFlyout) and self.flyout.actions.preview):
                self.smart.tick()
        else:
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
            self.flyout.show_flyout_at_tray()

    def _start_ipc_server(self):
        """Background localhost TCP socket listener for single-instance triggers."""
        def _server():
            try:
                while self._is_running:
                    try:
                        conn, _ = self._server_sock.accept()
                        with conn:
                            conn.settimeout(0.5)
                            data, nonces = authenticate_request(conn, self._ipc_token)

                            handled = False
                            cmd_upper = data.upper()
                            if cmd_upper == "TOGGLE":
                                self._schedule_on_main(lambda: self.toggle_nightlight(show_hud=True))
                                handled = True
                            elif cmd_upper == "START":
                                handled = True
                            elif cmd_upper == "QUIT":
                                handled = True
                            elif cmd_upper in ("PAUSE_SMART", "RESUME_SMART"):
                                self._schedule_on_main(lambda pause=cmd_upper=="PAUSE_SMART": self.taskbar_smart(pause))
                                handled = True
                            elif cmd_upper in ("SHOW", "ADJUST", "OPEN"):
                                self._schedule_on_main(self.show_flyout)
                                handled = True
                            elif cmd_upper.split()[:1] == ["PRESET"]:
                                parts = data.split()
                                if len(parts) == 2 and parts[1].isdigit():
                                    k = max(1000, min(6500, int(parts[1])))
                                    self._schedule_on_main(lambda k=k: self.apply_preset(k))
                                    handled = True
                            elif cmd_upper.split()[:1] == ["STRENGTH"]:
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

                            acknowledge(conn, self._ipc_token, data, nonces, handled)
                            if handled and cmd_upper=='QUIT':
                                self._schedule_on_main(self.quit_app)
                    except socket.timeout:
                        continue
                    except (ConnectionResetError, BrokenPipeError, UnicodeError, ValueError):
                        continue
                    except OSError:
                        if self._is_running:
                            continue
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
        self._clean_exit_requested = True
        self.cleanup()
        if self.root:
            try:
                self.root.quit()
                self.root.destroy()
            except Exception:
                pass
        sys.exit(0)

    def cleanup(self):
        self._is_running = False
        migrating=self.migration_interlocked()
        if migrating:self._migration.close()
        if is_v2_controller(getattr(self,'smart',None)):self.smart.close()
        if isinstance(getattr(self,'flyout',None), PremiumFlyout):self.flyout.close()
        if getattr(self,'emergency_hotkey',None):self.emergency_hotkey.close()
        try:
            if migrating:
                pass  # Worker persists Off; never block Tk on migration storage.
            elif getattr(self,'_clean_exit_requested',False):
                config.finish_session()
            else:
                config.save_immediate()
        except Exception as error:
            print(f'[Night Light] Cleanup configuration save failed: {error}')
        for attribute, operation in (('tray_icon', 'stop'), ('_server_sock', 'close')):
            resource = getattr(self, attribute, None)
            if resource is not None:
                try:
                    getattr(resource, operation)()
                    setattr(self, attribute, None)
                except Exception as error:
                    print(f'[Night Light] Cleanup {attribute} failed: {error}')
