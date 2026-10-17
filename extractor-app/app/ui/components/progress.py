"""Progress components — مطابق طرح داشبورد."""
from __future__ import annotations

import tkinter as tk
from typing import Optional

import customtkinter as ctk
from PIL import Image, ImageDraw, ImageTk

from app.formatters import fa_digits
from app.ui.components.cards import RtlLabel
from app.ui.platform_icons import pack_icon
from app.ui.tokens import CARD_RADIUS, COLORS, SPACE_MD, SPACE_SM, SPACE_XS
from app.ui.typography import font
from app.ui_components import create_gradient_image


def _c(color) -> str:
    if isinstance(color, (tuple, list)):
        return str(color[0])
    return str(color)


class ProgressBar(ctk.CTkFrame):
    """نوار پیشرفت بنفش ضخیم."""

    def __init__(self, master, height: int = 12, **kw):
        super().__init__(
            master,
            height=height + 6,
            corner_radius=height // 2 + 3,
            fg_color=COLORS["progress_track"],
            border_width=0,
            **kw,
        )
        self.pack_propagate(False)
        self._height = height
        self._value = 0.0
        self._canvas = tk.Canvas(self, height=height, highlightthickness=0, bd=0, bg=_c(COLORS["progress_track"]))
        self._canvas.pack(fill="x", expand=True, padx=3, pady=3)
        self._photo: Optional[ImageTk.PhotoImage] = None
        self.bind("<Configure>", lambda _e: self._redraw())
        self.after(50, self._redraw)

    def set(self, value: float) -> None:
        self._value = max(0.0, min(1.0, value))
        self._redraw()

    def _redraw(self) -> None:
        self._canvas.delete("all")
        w = self._canvas.winfo_width()
        h = self._height
        if w < 4:
            return
        self._canvas.configure(height=h, bg=_c(COLORS["progress_track"]))
        track = create_gradient_image(w, h, _c(COLORS["progress_track"]), _c(COLORS["progress_track"]))
        self._track_photo = ImageTk.PhotoImage(track)
        self._canvas.create_image(0, 0, anchor="nw", image=self._track_photo)
        fill_w = max(0, int(w * self._value))
        if fill_w > 2:
            grad = create_gradient_image(fill_w, h, _c(COLORS["primary"]), _c(COLORS["primary_end"]))
            self._photo = ImageTk.PhotoImage(grad)
            self._canvas.create_image(0, 0, anchor="nw", image=self._photo)


GradientProgressBar = ProgressBar


class CircularProgress(ctk.CTkFrame):
    """حلقه پیشرفت کلی — ۳ از ۱۲."""

    def __init__(self, master, size: int = 88, **kw):
        super().__init__(master, fg_color="transparent", width=size, height=size, **kw)
        self.pack_propagate(False)
        self._size = size
        self._frac = 0.0
        self._primary_label = "—"
        self._secondary_label = ""
        self._canvas = tk.Canvas(self, width=size, height=size, highlightthickness=0, bd=0, bg=_c(COLORS["card_bg"]))
        self._canvas.pack()
        self._photo: Optional[ImageTk.PhotoImage] = None
        self.after(30, self._redraw)

    def set(self, frac: float, primary_label: str, secondary_label: str = "") -> None:
        self._frac = max(0.0, min(1.0, frac))
        self._primary_label = primary_label
        self._secondary_label = secondary_label
        self._redraw()

    def _redraw(self) -> None:
        s = self._size
        img = Image.new("RGBA", (s, s), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        pad = 6
        track = _c(COLORS["progress_track"])
        primary = _c(COLORS["primary"])
        draw.ellipse([pad, pad, s - pad, s - pad], outline=track, width=8)
        if self._frac > 0.001:
            extent = -int(360 * self._frac)
            draw.arc([pad, pad, s - pad, s - pad], start=90, end=90 + extent, fill=primary, width=8)
        self._photo = ImageTk.PhotoImage(img)
        self._canvas.delete("all")
        self._canvas.configure(bg=_c(COLORS["card_bg"]))
        self._canvas.create_image(s // 2, s // 2, image=self._photo)
        self._canvas.create_text(
            s // 2, s // 2 - 8, text=self._primary_label, fill=_c(COLORS["text_primary"]),
            font=(font(12, "bold").cget("family"), 13, "bold"),
        )
        self._canvas.create_text(
            s // 2, s // 2 + 9, text=self._secondary_label or f"{fa_digits(int(self._frac * 100))}٪",
            fill=_c(COLORS["text_secondary"]), font=(font(10).cget("family"), 9),
        )


class ProgressCard(ctk.CTkFrame):
    """کارت پیشرفت اصلی مطابق طرح."""

    def __init__(self, master, **kw):
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

        top = ctk.CTkFrame(body, fg_color="transparent")
        top.pack(fill="x", pady=(0, SPACE_SM))

        title_col = ctk.CTkFrame(top, fg_color="transparent")
        title_col.pack(side="right", fill="x", expand=True)

        head = ctk.CTkFrame(title_col, fg_color="transparent")
        head.pack(fill="x")
        pack_icon(head, "download", size=16, side="right", padx=(SPACE_XS, 0))
        RtlLabel(head, "استخراج در حال انجام است", size=13, bold=True).pack(side="right")

        self.current_task_lbl = RtlLabel(title_col, "آماده برای شروع", size=12, muted=True)
        self.current_task_lbl.pack(anchor="e", pady=(4, 0))

        self.stat_done = RtlLabel(title_col, "", size=11, muted=True)
        self.stat_done.pack(anchor="e", pady=(2, 0))
        self.stat_total = RtlLabel(title_col, "", size=1)
        self.stat_total.pack_forget()
        self.stat_success = RtlLabel(title_col, "", size=1)
        self.stat_success.pack_forget()

        self.progress_percent = RtlLabel(top, "۰٪", size=22, bold=True)
        self.progress_percent.configure(text_color=COLORS["primary"])
        self.progress_percent.pack(side="left", padx=(SPACE_MD, 0))

        self.progress = ProgressBar(body, height=12)
        self.progress.pack(fill="x", pady=(SPACE_SM, 0))
        self.progress.set(0)

        self.scrape_time_info = RtlLabel(body, "", size=10, muted=True)
        self.scrape_time_info.pack(anchor="e", pady=(SPACE_XS, 0))


class OverallProgressCard(ctk.CTkFrame):
    """کارت پیشرفت کلی با حلقه."""

    def __init__(self, master, **kw):
        super().__init__(
            master,
            corner_radius=CARD_RADIUS,
            fg_color=COLORS["card_bg"],
            border_width=1,
            border_color=COLORS["card_border"],
            width=130,
            **kw,
        )
        inner = ctk.CTkFrame(self, fg_color="transparent")
        inner.pack(fill="both", expand=True, padx=SPACE_SM, pady=SPACE_MD)
        RtlLabel(inner, "پیشرفت کلی", size=10, muted=True).pack(anchor="center")
        self.ring = CircularProgress(inner, size=92)
        self.ring.pack(pady=(SPACE_SM, 0))
        self.value_lbl = RtlLabel(inner, "", size=1)
        self.value_lbl.pack_forget()
        self.hint_lbl = RtlLabel(inner, "زیردسته", size=10, muted=True)
        self.hint_lbl.pack(anchor="center", pady=(SPACE_XS, 0))

    def set_progress(self, completed: int, total: int, current_frac: float = 0.0) -> None:
        if total <= 0:
            self.ring.set(0, "—", "")
            return
        completed = max(0, min(total, completed))
        current_frac = max(0.0, min(1.0, current_frac))
        overall_frac = (completed + current_frac) / total
        primary = f"{fa_digits(completed)} / {fa_digits(total)}"
        secondary = "تکمیل‌شده"
        self.ring.set(overall_frac, primary, secondary)
