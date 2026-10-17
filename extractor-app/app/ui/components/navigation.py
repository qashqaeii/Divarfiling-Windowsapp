"""Navigation — نوار تب جدا از هدر، استایل pill حرفه‌ای."""
from __future__ import annotations

from typing import Callable, Dict

import customtkinter as ctk

from app.ui.icons import NAV_ITEMS
from app.ui.platform_icons import PlatformIconCache
from app.ui.tokens import COLORS, NAV_HEIGHT, RADIUS_MD, SPACE_LG, SPACE_SM, SPACE_XS
from app.ui.typography import font


class NavTab(ctk.CTkFrame):
    """تب pill — آیکن + عنوان."""

    def __init__(
        self,
        master,
        text: str,
        icon: str = "",
        *,
        tab_key: str = "",
        command=None,
        **kw,
    ):
        super().__init__(master, fg_color="transparent", **kw)
        self._active = False
        self._command = command
        self._tab_key = tab_key

        image = PlatformIconCache.nav_icon(tab_key, size=15) if tab_key else None
        self._btn = ctk.CTkButton(
            self,
            text=text if image is not None else (f"{icon}  {text}".strip() if icon else text),
            image=image,
            compound="right",
            command=self._click,
            height=34,
            width=0,
            corner_radius=RADIUS_MD,
            font=font(12, "bold"),
            fg_color="transparent",
            hover_color=COLORS["surface_secondary"],
            text_color=COLORS["text_secondary"],
            border_width=0,
        )
        self._btn.pack(side="top", padx=SPACE_XS, pady=0)

    def _click(self) -> None:
        if self._command:
            self._command()

    def set_active(self, active: bool) -> None:
        self._active = active
        if active:
            self._btn.configure(
                fg_color=COLORS["brand_soft"],
                text_color=COLORS["primary"],
                hover_color=COLORS["brand_soft"],
                border_width=1,
                border_color=COLORS["accent_glow"],
            )
        else:
            self._btn.configure(
                fg_color="transparent",
                text_color=COLORS["text_secondary"],
                hover_color=COLORS["surface_secondary"],
                border_width=0,
            )


class SegmentedNav(ctk.CTkFrame):
    """نوار ناوبری مستقل — زیر هدر."""

    def __init__(self, master, on_change: Callable[[str], None], **kw):
        super().__init__(
            master,
            fg_color=COLORS["app_bg_alt"],
            corner_radius=0,
            height=NAV_HEIGHT,
            **kw,
        )
        self.pack_propagate(False)
        self.grid_columnconfigure(0, weight=1)

        self._inner = ctk.CTkFrame(self, fg_color="transparent")
        self._inner.pack(side="right", padx=SPACE_LG, pady=SPACE_SM)

        self._tabs: Dict[str, NavTab] = {}
        self._on_change = on_change
        self._active = ""

        ctk.CTkFrame(self, height=1, fg_color=COLORS["header_border"]).place(
            relx=0, rely=1, relwidth=1, anchor="sw",
        )

    def add_tabs(self, keys: tuple[str, ...]) -> None:
        for key in keys:
            icon, label = NAV_ITEMS.get(key, ("", key))
            btn = NavTab(
                self._inner,
                text=label,
                icon=icon,
                tab_key=key,
                command=lambda k=key: self._select(k),
            )
            btn.pack(side="right", padx=(SPACE_XS, 0))
            self._tabs[key] = btn

    def _select(self, key: str) -> None:
        self.set_active(key)
        self._on_change(key)

    def set_active(self, key: str) -> None:
        self._active = key
        for name, btn in self._tabs.items():
            btn.set_active(name == key)


TabPill = NavTab
