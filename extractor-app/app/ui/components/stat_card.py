"""Stat card component."""
from __future__ import annotations

import customtkinter as ctk

from app.ui.components.cards import RtlLabel
from app.ui.platform_icons import pack_icon
from app.ui.tokens import CARD_RADIUS, COLORS, SPACE_SM
from app.ui.typography import stat_number


class StatCard(ctk.CTkFrame):
    """کارت آماری فشرده — برچسب راست، مقدار چپِ آن."""

    def __init__(self, master, label: str, value: str = "—", *, accent: bool = False, icon_key: str = "", **kw):
        border = COLORS["primary"] if accent else COLORS["card_border"]
        super().__init__(
            master,
            corner_radius=CARD_RADIUS,
            fg_color=COLORS["card_bg"],
            border_width=1,
            border_color=border,
            **kw,
        )
        inner = ctk.CTkFrame(self, fg_color="transparent")
        inner.pack(fill="both", expand=True, padx=SPACE_SM, pady=SPACE_SM)

        value_row = ctk.CTkFrame(inner, fg_color="transparent")
        value_row.pack(fill="x", anchor="e")
        self._val = RtlLabel(value_row, value, size=18, bold=True)
        self._val.pack(side="right")
        if icon_key:
            pack_icon(value_row, icon_key, size=14, side="right", padx=(SPACE_SM, 0))
        if accent:
            self._val.configure(text_color=COLORS["primary"])

        RtlLabel(inner, label, size=10, muted=True).pack(side="right", anchor="e", pady=(4, 0))

    def set_value(self, text: str) -> None:
        self._val.configure(text=text)
