"""Empty state component."""
from __future__ import annotations

from typing import Callable, Optional

import customtkinter as ctk

from app.ui.components.buttons import PrimaryButton
from app.ui.components.cards import RtlLabel
from app.ui.platform_icons import PlatformIconCache
from app.ui.tokens import CARD_RADIUS, COLORS, SPACE_LG, SPACE_MD
from app.ui.typography import font


class EmptyState(ctk.CTkFrame):
    """حالت خالی — آیکن، عنوان، توضیح، CTA."""

    def __init__(
        self,
        master,
        *,
        icon_key: str = "",
        icon: str = "",
        title: str = "",
        description: str = "",
        action_text: str = "",
        on_action: Optional[Callable] = None,
        **kw,
    ):
        super().__init__(
            master,
            corner_radius=CARD_RADIUS,
            fg_color=COLORS["surface_secondary"],
            border_width=1,
            border_color=COLORS["card_border"],
            **kw,
        )
        inner = ctk.CTkFrame(self, fg_color="transparent")
        inner.pack(expand=True, fill="both", padx=SPACE_LG, pady=SPACE_LG)

        image = PlatformIconCache.get(icon_key, 40) if icon_key else None
        if image is not None:
            ctk.CTkLabel(inner, text="", image=image, fg_color="transparent").pack(
                pady=(SPACE_MD, SPACE_MD),
            )
        elif icon:
            ctk.CTkLabel(
                inner, text=icon, font=font(28), text_color=COLORS["text_muted"],
            ).pack(pady=(SPACE_MD, SPACE_MD))
        RtlLabel(inner, title, size=15, bold=True).pack(anchor="center")
        if description:
            RtlLabel(inner, description, size=12, muted=True, wraplength=400).pack(
                anchor="center", pady=(SPACE_MD, SPACE_MD),
            )
        if action_text and on_action:
            PrimaryButton(inner, action_text, on_action, icon_key="rocket", width=180, height=38).pack()
