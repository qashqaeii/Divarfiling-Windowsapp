"""Path field with ellipsis."""
from __future__ import annotations

import customtkinter as ctk

from app.ui.components.buttons import GhostButton, IconButton
from app.ui.components.cards import FieldLabel, RtlLabel
from app.ui.platform_icons import pack_icon
from app.ui.tokens import CARD_RADIUS, COLORS, SPACE_MD, SPACE_SM
from app.ui.typography import mono_font


def truncate_path(path: str, max_len: int = 48) -> str:
    path = (path or "").strip()
    if not path:
        return ""
    if len(path) <= max_len:
        return path
    return "…" + path[-(max_len - 1):]


class PathField(ctk.CTkFrame):
    """نمایش مسیر کوتاه‌شده با دکمه‌های عملیات."""

    def __init__(
        self,
        master,
        label: str,
        value: str = "",
        *,
        icon_key: str = "folder",
        on_copy=None,
        on_open=None,
        muted: bool = False,
        **kw,
    ):
        super().__init__(
            master,
            corner_radius=CARD_RADIUS,
            fg_color=COLORS["card_bg"],
            border_width=1,
            border_color=COLORS["card_border"],
            **kw,
        )
        body = ctk.CTkFrame(self, fg_color="transparent")
        body.pack(fill="both", expand=True, padx=SPACE_MD, pady=SPACE_MD)

        head = ctk.CTkFrame(body, fg_color="transparent")
        head.pack(fill="x", pady=(0, SPACE_SM))
        if icon_key:
            pack_icon(head, icon_key, size=14, side="right")
        FieldLabel(head, label).pack(side="right", padx=(SPACE_SM, 0))

        btns = ctk.CTkFrame(head, fg_color="transparent")
        btns.pack(side="left")
        if on_copy:
            IconButton(btns, icon_key="copy", command=on_copy, size=28).pack(side="left", padx=2)
        if on_open:
            IconButton(btns, icon_key="folder", command=on_open, size=28).pack(side="left", padx=2)

        self._full_path = value
        self.value_lbl = ctk.CTkLabel(
            body,
            text=truncate_path(value),
            font=mono_font(11),
            text_color=COLORS["text_secondary"] if muted else COLORS["text_primary"],
            anchor="e",
            justify="right",
            wraplength=400,
        )
        self.value_lbl.pack(fill="x", anchor="e")

    def set_value(self, path: str, *, muted: bool = False) -> None:
        self._full_path = path
        display = truncate_path(path, 64)
        self.value_lbl.configure(
            text=display or "—",
            text_color=COLORS["text_secondary"] if muted else COLORS["text_primary"],
        )

    @property
    def full_path(self) -> str:
        return self._full_path
