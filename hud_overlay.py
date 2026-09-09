"""
Modern HUD Toast Overlay for Night Light by HT.
Provides instant visual feedback when toggling Night Light from the pinned taskbar button.
"""

import ctypes
from ctypes import wintypes
import tkinter as tk
from typing import Optional
import customtkinter as ctk

user32 = ctypes.windll.user32


class RECT(ctypes.Structure):
    _fields_ = [("left", wintypes.LONG), ("top", wintypes.LONG), ("right", wintypes.LONG), ("bottom", wintypes.LONG)]


class MONITORINFO(ctypes.Structure):
    _fields_ = [("cbSize", wintypes.DWORD), ("rcMonitor", RECT), ("rcWork", RECT), ("dwFlags", wintypes.DWORD)]


class HudToast(ctk.CTkToplevel):
    def __init__(self, master, on_click=None):
        super().__init__(master)
        self.on_click = on_click
        self.overrideredirect(True)
        self.attributes("-topmost", True)
        self.resizable(False, False)

        self.width = 330
        self.height = 48
        self._hide_job = None

        self.configure(fg_color="#18191d")

        self.card = ctk.CTkFrame(
            self,
            fg_color="#202228",
            border_color="#ffaa2b",
            border_width=1,
            corner_radius=10,
        )
        self.card.pack(fill="both", expand=True, padx=2, pady=2)

        self.icon_label = ctk.CTkLabel(
            self.card,
            text="🌙",
            font=ctk.CTkFont(size=18),
            text_color="#ffaa2b",
        )
        self.icon_label.pack(side="left", padx=(14, 6))

        self.msg_label = ctk.CTkLabel(
            self.card,
            text="Night Light by HT ON · 70% Strength",
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
            text_color="#ffffff",
            anchor="w",
        )
        self.msg_label.pack(side="left", fill="both", expand=True, padx=4)

        for w in (self, self.card, self.icon_label, self.msg_label):
            w.bind("<Button-1>", lambda e: self._on_clicked())

        self.withdraw()

    def _on_clicked(self):
        self.hide()
        if self.on_click:
            self.on_click()

    def show(
        self,
        is_enabled: bool,
        strength_pct: int,
        kelvin: int,
        is_effective: bool = True,
        detail: str = "",
    ):
        if self._hide_job:
            self.after_cancel(self._hide_job)

        if is_enabled and not is_effective:
            self.card.configure(border_color="#facc15")
            self.icon_label.configure(text="⏸", text_color="#facc15")
            self.msg_label.configure(text=f"Night Light by HT PAUSED · {detail}")
        elif is_enabled:
            self.card.configure(border_color="#ffaa2b")
            self.icon_label.configure(text="🌙", text_color="#ffaa2b")
            self.msg_label.configure(text=f"Night Light by HT ON · {strength_pct}% Strength ({kelvin}K)")
        else:
            self.card.configure(border_color="#3b82f6")
            self.icon_label.configure(text="☀️", text_color="#60a5fa")
            self.msg_label.configure(text="Night Light by HT OFF · Daylight Restored")

        # Position at bottom-right of active monitor work area
        pt = wintypes.POINT()
        user32.GetCursorPos(ctypes.byref(pt))
        hmonitor = user32.MonitorFromPoint(pt, 2)  # MONITOR_DEFAULTTONEAREST

        mi = MONITORINFO()
        mi.cbSize = ctypes.sizeof(MONITORINFO)
        user32.GetMonitorInfoW(hmonitor, ctypes.byref(mi))

        pos_x = mi.rcWork.right - self.width - 16
        pos_y = mi.rcWork.bottom - self.height - 12

        self.geometry(f"{self.width}x{self.height}+{pos_x}+{pos_y}")
        self.deiconify()
        self.lift()

        # Auto-dismiss after 2 seconds
        self._hide_job = self.after(2000, self.hide)

    def hide(self):
        self.withdraw()
