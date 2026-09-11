"""Isolated embedded-renderer QA; never binds production IPC or display APIs."""
import os
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
if os.environ.get('NIGHT_LIGHT_BY_HT_DISABLE_DISPLAY_BACKEND')!='1' or not os.environ.get('NIGHT_LIGHT_BY_HT_CONFIG_DIR'):
    raise SystemExit('QA requires disabled display backend and isolated config directory.')
import customtkinter as ctk
from types import SimpleNamespace
from config_manager import ConfigManager
from nightlight_engine import NightLightEngine
from smart_mode import SmartController
from premium_ui import PremiumFlyout
from display_status import derive_display_status
c=ConfigManager();e=NightLightEngine();root=ctk.CTk();root.withdraw();e.set_gui_dispatcher(root.after)
s=SmartController(e,c);s.configure(42.3353,-83.2864)
app=SimpleNamespace(root=root,smart=s,turn_windows_nightlight_off=lambda:None,quit_app=lambda:root.quit(),_get_display_status=lambda:derive_display_status(app_enabled=e.is_enabled,brightness=e.brightness,windows_active=False,backend_applied=e.is_applied))
app.flyout=PremiumFlyout(app,e,c)
app.flyout.show_flyout_at_tray()
root.after(900000,root.quit)
try:root.mainloop()
finally:app.flyout.close();root.destroy()
