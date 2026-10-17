"""Status bar — مسیر | نسخه | آخرین به‌روزرسانی."""
from __future__ import annotations

from typing import Callable, Optional

import customtkinter as ctk

from app.ui.components.cards import RtlLabel, StatusChip
from app.ui.platform_icons import pack_icon
from app.ui.tokens import APP_VERSION, COLORS, SPACE_MD, SPACE_SM, STATUSBAR_HEIGHT
from app.ui.typography import font, mono_font


class AppStatusBar(ctk.CTkFrame):
    """نوار وضعیت پایین مطابق طرح."""

    def __init__(
        self,
        master,
        *,
        version: str = APP_VERSION,
        on_path_click: Optional[Callable] = None,
        **kw,
    ):
        super().__init__(master, fg_color="transparent", corner_radius=0, **kw)
        self.pack_propagate(False)
        self.configure(height=STATUSBAR_HEIGHT + 1)

        ctk.CTkFrame(self, height=1, corner_radius=0, fg_color=COLORS["statusbar_border"]).pack(fill="x")

        bar = ctk.CTkFrame(
            self, height=STATUSBAR_HEIGHT, corner_radius=0,
            fg_color=COLORS["statusbar_bg"], border_width=0,
        )
        bar.pack(fill="both", expand=True)
        bar.pack_propagate(False)

        inner = ctk.CTkFrame(bar, fg_color="transparent")
        inner.pack(fill="both", expand=True, padx=SPACE_MD)

        # راست: آخرین به‌روزرسانی
        right = ctk.CTkFrame(inner, fg_color="transparent")
        right.pack(side="right")
        self._update_lbl = RtlLabel(right, "آخرین به‌روزرسانی: —", size=9, muted=True)
        self._update_lbl.pack(side="right")

        # پنهان برای سازگاری
        self._stat_extract = StatusChip(inner, "استخراج", "آماده", tone="success", icon_key="extract")
        self._stat_license = StatusChip(inner, "لایسنس", "…", tone="muted", icon_key="license")
        self._stat_extract.pack_forget()
        self._stat_license.pack_forget()

        # وسط: نسخه
        self.version_lbl = RtlLabel(inner, f"نسخه {version}", size=9, muted=True)
        self.version_lbl.place(relx=0.5, rely=0.5, anchor="center")

        # چپ: مسیر خروجی
        path_wrap = ctk.CTkFrame(inner, fg_color="transparent")
        path_wrap.pack(side="left", fill="x", expand=True)
        pack_icon(path_wrap, "folder", size=12, side="left", padx=(0, 4))
        self.status_path_lbl = RtlLabel(path_wrap, "", size=9, muted=True)
        self.status_path_lbl.configure(font=mono_font(9), anchor="w", justify="left")
        self.status_path_lbl.pack(side="left", fill="x", expand=True)

        self.status_lbl = RtlLabel(inner, "آماده", size=9, muted=True)
        self.status_lbl.pack_forget()

    def set_message(self, text: str, *, tone: str = "muted") -> None:
        msg = (text or "آماده")[:80]
        self._update_lbl.configure(text=f"وضعیت: {msg}")
