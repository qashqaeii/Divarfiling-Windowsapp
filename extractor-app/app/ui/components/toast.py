"""Toast notification."""
from __future__ import annotations

import customtkinter as ctk

from app.ui.platform_icons import pack_icon
from app.ui.tokens import COLORS, SPACE_MD, SPACE_SM
from app.ui.typography import font


class Toast:
    """پیام موقت — سبک و بدون انیمیشن سنگین."""

    _TONES = {
        "success": ("success_bg", "success", "success_border", "sparkles"),
        "error": ("error_bg", "error", "error_border", "filter"),
        "warning": ("warning_bg", "warning", "warning_border", "bell"),
        "info": ("info_bg", "info", "info_border", "help_center"),
    }

    @classmethod
    def show(cls, root: ctk.CTk, message: str, *, tone: str = "success", duration_ms: int = 2800) -> None:
        bg, fg, border, icon_key = cls._TONES.get(tone, cls._TONES["info"])
        toast = ctk.CTkFrame(
            root,
            corner_radius=10,
            fg_color=COLORS[bg],
            border_width=1,
            border_color=COLORS[border],
        )
        row = ctk.CTkFrame(toast, fg_color="transparent")
        row.pack(padx=SPACE_MD, pady=10)
        pack_icon(row, icon_key, size=16, side="right", padx=(SPACE_SM, 0))
        lbl = ctk.CTkLabel(row, text=message, font=font(12), text_color=COLORS[fg])
        lbl.pack(side="right")
        toast.place(relx=0.5, rely=0.92, anchor="center")
        toast.lift()

        def _hide() -> None:
            try:
                toast.destroy()
            except Exception:
                pass

        root.after(duration_ms, _hide)
