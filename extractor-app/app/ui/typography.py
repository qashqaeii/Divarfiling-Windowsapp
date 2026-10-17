"""Typography helpers — RTL Persian fonts."""
from __future__ import annotations

import sys

import customtkinter as ctk

FONT_FAMILY = "B Nazanin"
FALLBACK_FONT = "Tahoma"
MONO_FAMILY = "Consolas" if sys.platform == "win32" else "Courier New"


def font(size: int = 14, weight: str = "normal") -> ctk.CTkFont:
    family = FONT_FAMILY if sys.platform == "win32" else FALLBACK_FONT
    return ctk.CTkFont(family=family, size=size, weight=weight)


def mono_font(size: int = 12, weight: str = "normal") -> ctk.CTkFont:
    return ctk.CTkFont(family=MONO_FAMILY, size=size, weight=weight)


def heading(size: int = 18) -> ctk.CTkFont:
    return font(size, "bold")


def page_title(size: int = 16) -> ctk.CTkFont:
    return font(size, "bold")


def card_title(size: int = 13) -> ctk.CTkFont:
    return font(size, "bold")


def label(size: int = 12) -> ctk.CTkFont:
    return font(size, "bold")


def body(size: int = 13) -> ctk.CTkFont:
    return font(size, "normal")


def caption(size: int = 11) -> ctk.CTkFont:
    return font(size, "normal")


def stat_number(size: int = 22) -> ctk.CTkFont:
    return font(size, "bold")


def status(size: int = 11) -> ctk.CTkFont:
    return font(size, "bold")
