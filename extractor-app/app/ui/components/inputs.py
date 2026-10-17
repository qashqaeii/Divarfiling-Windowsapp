"""Input components."""
from __future__ import annotations

import customtkinter as ctk

from app.ui.tokens import COLORS, INPUT_HEIGHT, INPUT_RADIUS, SPACE_SM
from app.ui.typography import font


def styled_entry(parent, **kwargs) -> ctk.CTkEntry:
    defaults = {
        "justify": "right",
        "font": font(14),
        "height": INPUT_HEIGHT,
        "corner_radius": INPUT_RADIUS,
        "border_color": COLORS["input_border"],
        "fg_color": COLORS["input_bg"],
        "border_width": 1,
    }
    defaults.update(kwargs)
    return ctk.CTkEntry(parent, **defaults)


class AppInput(ctk.CTkFrame):
    """ورودی با برچسب و متن راهنما."""

    def __init__(
        self,
        master,
        label: str = "",
        *,
        placeholder: str = "",
        hint: str = "",
        readonly: bool = False,
        ltr: bool = False,
        **entry_kw,
    ):
        super().__init__(master, fg_color="transparent")
        from app.ui.components.cards import FieldLabel, RtlLabel

        if label:
            FieldLabel(self, label).pack(anchor="e", pady=(0, 4))
        justify = "left" if ltr else "right"
        self.entry = styled_entry(self, placeholder_text=placeholder, justify=justify, **entry_kw)
        self.entry.pack(fill="x")
        if hint:
            RtlLabel(self, hint, size=10, muted=True, wraplength=300).pack(anchor="e", pady=(4, 0))
        if readonly:
            self.entry.configure(state="readonly")


class SearchInput(ctk.CTkFrame):
    """ورودی جستجو با آیکن و دکمه پاک‌کردن."""

    def __init__(self, master, placeholder: str = "جستجو…", on_search=None, on_clear=None, **kw):
        super().__init__(master, fg_color="transparent", **kw)
        from app.ui.components.buttons import GhostButton, IconButton

        row = ctk.CTkFrame(self, fg_color="transparent")
        row.pack(fill="x")

        self.entry = styled_entry(row, placeholder_text=placeholder)
        self.entry.pack(side="right", fill="x", expand=True)

        if on_clear:
            IconButton(row, icon_key="clear", command=on_clear, size=30).pack(side="right", padx=(SPACE_SM, 0))
        if on_search:
            IconButton(row, icon_key="search", command=on_search, size=30).pack(side="right", padx=(SPACE_SM, 0))

    def get(self) -> str:
        return self.entry.get()

    def delete(self, first, last=None) -> None:
        self.entry.delete(first, last)

    def insert(self, index, text) -> None:
        self.entry.insert(index, text)

    def bind_return(self, callback) -> None:
        self.entry.bind("<Return>", lambda _e: callback())
