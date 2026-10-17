"""Application header — برند و وضعیت (جدا از نوار تب‌ها)."""
from __future__ import annotations

from typing import Callable, Optional

import customtkinter as ctk

from app.ui.components.buttons import IconButton
from app.ui.components.cards import RtlLabel
from app.ui.tokens import COLORS, HEADER_HEIGHT, SPACE_LG, SPACE_MD, SPACE_SM, SPACE_XS
from app.ui.typography import font


class AppHeader(ctk.CTkFrame):
    """هدر برند + وضعیت — بدون تب‌ها."""

    def __init__(
        self,
        master,
        *,
        brand_name: str,
        brand_tagline: str,
        logo_image: Optional[ctk.CTkImage] = None,
        logo_fallback: str = "د",
        on_notifications_click: Optional[Callable[[], None]] = None,
        on_settings_click: Optional[Callable[[], None]] = None,
        on_profile_click: Optional[Callable[[], None]] = None,
        height: int = HEADER_HEIGHT,
        **kw,
    ):
        super().__init__(master, fg_color=COLORS["header_bg"], corner_radius=0, **kw)
        self.grid_columnconfigure(0, weight=1)

        top = ctk.CTkFrame(self, fg_color="transparent", height=height)
        top.grid(row=0, column=0, sticky="ew")
        top.pack_propagate(False)
        top.grid_columnconfigure(1, weight=1)

        # راست: برند
        brand = ctk.CTkFrame(top, fg_color="transparent")
        brand.pack(side="right", padx=(SPACE_SM, SPACE_LG), pady=SPACE_SM)

        logo = ctk.CTkFrame(
            brand, width=40, height=40, corner_radius=12,
            fg_color=COLORS["primary"],
        )
        logo.pack(side="right", padx=(SPACE_SM, 0))
        logo.pack_propagate(False)
        if logo_image:
            ctk.CTkLabel(logo, text="", image=logo_image, fg_color="transparent").place(
                relx=0.5, rely=0.5, anchor="center",
            )
        else:
            ctk.CTkLabel(
                logo, text=logo_fallback, font=font(16, "bold"),
                text_color=COLORS["accent_text"],
            ).place(relx=0.5, rely=0.5, anchor="center")

        titles = ctk.CTkFrame(brand, fg_color="transparent")
        titles.pack(side="right")
        RtlLabel(titles, brand_name, size=16, bold=True).pack(anchor="e")
        if brand_tagline:
            RtlLabel(titles, brand_tagline, size=10, muted=True).pack(anchor="e")

        # چپ: وضعیت + آیکن‌ها
        status_host = ctk.CTkFrame(top, fg_color="transparent")
        status_host.pack(side="left", padx=(SPACE_LG, SPACE_SM), pady=SPACE_SM)

        self.profile_btn = IconButton(
            status_host, icon_key="user", size=32, command=on_profile_click, tooltip="پروفایل و لایسنس",
        )
        self.profile_btn.pack(side="left", padx=(0, 2))
        self.settings_btn = IconButton(
            status_host, icon_key="settings", size=32, command=on_settings_click, tooltip="تنظیمات",
        )
        self.settings_btn.pack(side="left", padx=(0, 2))
        self.notifications_btn = IconButton(
            status_host, icon_key="bell", size=32, command=on_notifications_click, tooltip="اعلان‌ها",
        )
        self.notifications_btn.pack(side="left", padx=(0, SPACE_MD))

        self.chip_license = _HeaderStatus(
            status_host, "لایسنس فعال", tone="brand", icon="✓",
        )
        self.chip_license.pack(side="left", padx=(0, SPACE_SM))
        self.chip_connection = _HeaderStatus(
            status_host, "اتصال برقرار", tone="success",
        )
        self.chip_connection.pack(side="left")


class _HeaderStatus(ctk.CTkFrame):
    """نشان وضعیت هدر — نقطه رنگی + متن."""

    def __init__(self, master, text: str, *, tone: str = "muted", icon: str = ""):
        super().__init__(master, fg_color="transparent")
        row = ctk.CTkFrame(self, fg_color="transparent")
        row.pack()
        color = {
            "success": COLORS["success"],
            "brand": COLORS["primary"],
            "muted": COLORS["text_muted"],
        }.get(tone, COLORS["text_muted"])
        if icon:
            ctk.CTkLabel(row, text=icon, font=font(11, "bold"), text_color=color, width=14).pack(side="right")
        else:
            ctk.CTkFrame(row, width=8, height=8, corner_radius=4, fg_color=color).pack(
                side="right", padx=(0, SPACE_XS),
            )
        self._lbl = RtlLabel(row, text, size=11, bold=True)
        self._lbl.pack(side="right", padx=(0, 4))
        self._tone = tone

    def set_value(self, text: str, *, tone: str | None = None) -> None:
        mapping = {
            "فعال": "لایسنس فعال",
            "غیرفعال": "لایسنس غیرفعال",
            "آنلاین": "اتصال برقرار",
            "آفلاین": "اتصال قطع",
        }
        self._lbl.configure(text=mapping.get(text, text))
        if tone:
            self._tone = tone
            color = {
                "success": COLORS["success"],
                "brand": COLORS["primary"],
                "error": COLORS["error"],
                "muted": COLORS["text_muted"],
            }.get(tone, COLORS["text_muted"])
            for child in self.winfo_children():
                for sub in child.winfo_children():
                    try:
                        if isinstance(sub, ctk.CTkFrame) and sub.winfo_width() <= 10:
                            sub.configure(fg_color=color)
                        elif isinstance(sub, ctk.CTkLabel) and sub.cget("text") in ("✓", "●"):
                            sub.configure(text_color=color)
                    except Exception:
                        pass


AppHeaderBar = AppHeader
