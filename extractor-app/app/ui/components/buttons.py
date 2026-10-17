"""Button components."""
from __future__ import annotations

from typing import Callable, Optional

import customtkinter as ctk

from app.ui.platform_icons import button_icon_kwargs
from app.ui.tokens import BUTTON_HEIGHT, BUTTON_RADIUS, COLORS
from app.ui.typography import font


class PrimaryButton(ctk.CTkButton):
    """CTA اصلی."""

    def __init__(
        self,
        master,
        text: str,
        command: Optional[Callable] = None,
        *,
        width: int = 140,
        height: int = BUTTON_HEIGHT,
        icon_key: str = "",
        icon: str = "",
        **kw,
    ):
        icon_kw = button_icon_kwargs(text, icon_key=icon_key, icon_size=16)
        if "image" not in icon_kw and icon:
            icon_kw["text"] = f"{icon}  {text}".strip()
        super().__init__(
            master,
            command=command,
            width=width,
            height=height,
            corner_radius=BUTTON_RADIUS,
            font=font(13, "bold"),
            fg_color=COLORS["primary"],
            hover_color=COLORS["primary_hover"],
            text_color=COLORS["accent_text"],
            border_width=0,
            **icon_kw,
            **kw,
        )


class SecondaryButton(ctk.CTkButton):
    def __init__(
        self, master, text: str, command=None, *, width=120, height=40,
        icon_key: str = "", **kw,
    ):
        kw.setdefault("font", font(12, "bold"))
        icon_kw = button_icon_kwargs(text, icon_key=icon_key, icon_size=15)
        super().__init__(
            master,
            command=command,
            width=width,
            height=height,
            corner_radius=BUTTON_RADIUS,
            fg_color=COLORS["surface_secondary"],
            hover_color=COLORS["card_bg_soft"],
            text_color=COLORS["text_primary"],
            border_width=1,
            border_color=COLORS["card_border"],
            **icon_kw,
            **kw,
        )


class GhostButton(ctk.CTkButton):
    def __init__(
        self, master, text: str, command=None, *, width=120, height=36,
        icon_key: str = "", **kw,
    ):
        kw.setdefault("font", font(12))
        icon_kw = button_icon_kwargs(text, icon_key=icon_key, icon_size=14)
        super().__init__(
            master,
            command=command,
            width=width,
            height=height,
            corner_radius=BUTTON_RADIUS,
            fg_color="transparent",
            hover_color=COLORS["brand_soft"],
            text_color=COLORS["primary"],
            border_width=0,
            **icon_kw,
            **kw,
        )


class OutlineButton(ctk.CTkButton):
    def __init__(
        self, master, text: str, command=None, *, width=120, height=40,
        icon_key: str = "", **kw,
    ):
        kw.setdefault("font", font(12, "bold"))
        icon_kw = button_icon_kwargs(text, icon_key=icon_key, icon_size=15)
        super().__init__(
            master,
            command=command,
            width=width,
            height=height,
            corner_radius=BUTTON_RADIUS,
            fg_color="transparent",
            hover_color=COLORS["card_bg_soft"],
            text_color=COLORS["text_primary"],
            border_width=1,
            border_color=COLORS["card_border"],
            **icon_kw,
            **kw,
        )


class DangerOutlineButton(ctk.CTkButton):
    def __init__(
        self, master, text: str, command=None, *, width=120, height=40,
        icon_key: str = "", **kw,
    ):
        kw.setdefault("font", font(12))
        icon_kw = button_icon_kwargs(text, icon_key=icon_key, icon_size=15)
        super().__init__(
            master,
            command=command,
            width=width,
            height=height,
            corner_radius=BUTTON_RADIUS,
            fg_color="transparent",
            hover_color=COLORS["error_bg"],
            text_color=COLORS["error"],
            border_width=1,
            border_color=COLORS["error_border"],
            **icon_kw,
            **kw,
        )


class IconButton(ctk.CTkButton):
    def __init__(
        self,
        master,
        icon_key: str = "",
        icon: str = "",
        command=None,
        *,
        size: int = 32,
        tooltip: str = "",
        **kw,
    ):
        image = None
        if icon_key:
            from app.ui.platform_icons import PlatformIconCache
            image = PlatformIconCache.get(icon_key, max(14, size - 10))
        if image is not None:
            super().__init__(
                master,
                text="",
                image=image,
                command=command,
                width=size,
                height=size,
                corner_radius=8,
                fg_color="transparent",
                hover_color=COLORS["card_bg_soft"],
                **kw,
            )
        else:
            super().__init__(
                master,
                text=icon,
                command=command,
                width=size,
                height=size,
                corner_radius=8,
                font=font(12),
                fg_color="transparent",
                hover_color=COLORS["card_bg_soft"],
                text_color=COLORS["text_secondary"],
                **kw,
            )
        self._tooltip = tooltip
