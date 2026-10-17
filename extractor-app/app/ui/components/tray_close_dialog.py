"""دیالوگ اولین بستن پنجره — توضیح اجرای پس‌زمینه در System Tray."""
from __future__ import annotations

from typing import Callable, Optional

import customtkinter as ctk

from app.brand import SITE_DISPLAY_NAME
from app.ui.components import OutlineButton, PrimaryButton, RtlLabel
from app.ui.platform_icons import PlatformIconCache, pack_icon
from app.ui.tokens import (
    COLORS,
    RADIUS_MD,
    SPACE_LG,
    SPACE_MD,
    SPACE_SM,
    SPACE_XS,
)
from app.ui.typography import font


def _center_window(win: ctk.CTkToplevel, width: int, height: int) -> None:
    win.update_idletasks()
    try:
        sw = win.winfo_screenwidth()
        sh = win.winfo_screenheight()
        x = max(0, (sw - width) // 2)
        y = max(0, (sh - height) // 3)
        win.geometry(f"{width}x{height}+{x}+{y}")
    except Exception:
        win.geometry(f"{width}x{height}")


class CloseToTrayDialog(ctk.CTkToplevel):
    """توضیح حرفه‌ای Hide-to-Tray با گزینه «دیگر نمایش نده»."""

    def __init__(
        self,
        master,
        *,
        on_confirm: Callable[[bool], None],
        on_quit_instead: Optional[Callable[[], None]] = None,
    ) -> None:
        super().__init__(master)
        self.title(f"{SITE_DISPLAY_NAME} — پس‌زمینه")
        self.resizable(False, False)
        self.transient(master)
        self.grab_set()
        self.configure(fg_color=COLORS["card_bg"])
        self._on_confirm = on_confirm
        self._on_quit_instead = on_quit_instead
        self._dont_show = ctk.BooleanVar(value=False)
        self._resolved = False

        _center_window(self, 460, 420)

        root = ctk.CTkFrame(self, fg_color=COLORS["card_bg"])
        root.pack(fill="both", expand=True, padx=SPACE_LG, pady=SPACE_LG)

        icon_wrap = ctk.CTkFrame(
            root, width=64, height=64, corner_radius=20, fg_color=COLORS["brand_soft"],
        )
        icon_wrap.pack(pady=(SPACE_SM, SPACE_MD))
        icon_wrap.pack_propagate(False)
        img = PlatformIconCache.get("settings", 28) or PlatformIconCache.get("bell", 28)
        if img is not None:
            lbl = ctk.CTkLabel(icon_wrap, text="", image=img, fg_color="transparent")
            lbl._icon_image = img
            lbl.place(relx=0.5, rely=0.5, anchor="center")
        else:
            ctk.CTkLabel(
                icon_wrap, text="▣", font=font(22, "bold"), text_color=COLORS["primary"],
            ).place(relx=0.5, rely=0.5, anchor="center")

        RtlLabel(root, "برنامه در پس‌زمینه می‌ماند", size=18, bold=True).pack(anchor="center")
        RtlLabel(
            root,
            f"با بستن پنجره، {SITE_DISPLAY_NAME} کاملاً بسته نمی‌شود؛ "
            "فقط مخفی می‌شود و استخراج، آپلود و زمان‌بندی‌ها ادامه پیدا می‌کنند.",
            size=12,
            muted=True,
            wraplength=380,
        ).pack(anchor="center", pady=(SPACE_XS, SPACE_MD))

        tips = ctk.CTkFrame(
            root,
            corner_radius=RADIUS_MD,
            fg_color=COLORS["surface_secondary"],
            border_width=1,
            border_color=COLORS["card_border"],
        )
        tips.pack(fill="x", pady=(0, SPACE_MD))
        tips_inner = ctk.CTkFrame(tips, fg_color="transparent")
        tips_inner.pack(fill="x", padx=SPACE_MD, pady=SPACE_SM)

        for text, icon_key in (
            ("آیکن برنامه در System Tray (کنار ساعت ویندوز) باقی می‌ماند.", "sparkles"),
            ("با دابل‌کلیک روی آیکن یا «باز کردن برنامه» دوباره پنجره را ببینید.", "rocket"),
            ("خروج واقعی فقط از منوی Tray یا تنظیمات («خروج کامل») است.", "stop"),
        ):
            row = ctk.CTkFrame(tips_inner, fg_color="transparent")
            row.pack(fill="x", pady=2)
            pack_icon(row, icon_key, size=14, side="right", padx=(SPACE_XS, 0))
            RtlLabel(row, text, size=11, wraplength=340).pack(side="right", fill="x", expand=True)

        ctk.CTkCheckBox(
            root,
            text="دیگر این پیام را نمایش نده",
            variable=self._dont_show,
            font=font(11),
            fg_color=COLORS["primary"],
            hover_color=COLORS["primary_hover"],
        ).pack(anchor="e", pady=(0, SPACE_MD))

        actions = ctk.CTkFrame(root, fg_color="transparent")
        actions.pack(fill="x")
        PrimaryButton(
            actions, "ادامه در پس‌زمینه", self._confirm, icon_key="save", height=38, width=170,
        ).pack(side="right")
        OutlineButton(
            actions, "خروج کامل", self._quit, icon_key="stop", height=38, width=120,
        ).pack(side="right", padx=(0, SPACE_SM))

        self.protocol("WM_DELETE_WINDOW", self._confirm)
        self.bind("<Escape>", lambda _e: self._confirm())
        self.after(30, self._focus_safe)

    def _focus_safe(self) -> None:
        try:
            self.lift()
            self.focus_force()
        except Exception:
            pass

    def _confirm(self) -> None:
        if self._resolved:
            return
        self._resolved = True
        dont_show = bool(self._dont_show.get())
        try:
            self.grab_release()
        except Exception:
            pass
        self.destroy()
        self._on_confirm(dont_show)

    def _quit(self) -> None:
        if self._resolved:
            return
        self._resolved = True
        try:
            self.grab_release()
        except Exception:
            pass
        self.destroy()
        if self._on_quit_instead:
            self._on_quit_instead()
