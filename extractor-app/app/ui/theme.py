"""Theme setup — appearance mode and font loading."""
from __future__ import annotations

import os
import sys

import customtkinter as ctk

from app.paths import get_resource_path
from app.ui.typography import FALLBACK_FONT, FONT_FAMILY


def try_load_windows_font(ttf_path: str) -> None:
    try:
        import ctypes
        if os.path.isfile(ttf_path):
            ctypes.windll.gdi32.AddFontResourceExW(ttf_path, 0x10 | 0x20, 0)
    except Exception:
        pass


def setup_theme() -> None:
    ctk.set_appearance_mode("light")
    ctk.set_default_color_theme("blue")
    try_load_windows_font(get_resource_path("fonts/B Nazanin.ttf"))
    try_load_windows_font(get_resource_path("fonts/B Nazanin Bold.ttf"))
    try:
        import tkinter.font as tkfont
        family = FONT_FAMILY if sys.platform == "win32" else FALLBACK_FONT
        for name in ("TkDefaultFont", "TkTextFont", "TkMenuFont", "TkHeadingFont"):
            try:
                tkfont.nametofont(name).configure(family=family)
            except Exception:
                pass
    except Exception:
        pass
