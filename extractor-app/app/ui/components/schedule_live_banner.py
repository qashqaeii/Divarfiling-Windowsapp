"""بنر وضعیت زنده زمان‌بندی — نمایش روشن بودن و هدف استخراج."""
from __future__ import annotations

from typing import Optional

import customtkinter as ctk

from app.formatters import fa_digits, format_duration_fa, format_timestamp_fa
from app.ui.components.cards import RtlLabel
from app.ui.platform_icons import pack_icon
from app.ui.tokens import CARD_RADIUS, COLORS, RADIUS_MD, SPACE_MD, SPACE_SM, SPACE_XS
from app.ui.typography import font


class ScheduleLiveBanner(ctk.CTkFrame):
    """کارت برجسته وضعیت زمان‌بندی برای کاربر نهایی."""

    def __init__(self, master, **kw):
        super().__init__(
            master,
            corner_radius=CARD_RADIUS,
            fg_color=COLORS["surface_secondary"],
            border_width=1,
            border_color=COLORS["card_border"],
            **kw,
        )
        self._pulse_on = False
        self._pulse_id: Optional[str] = None

        inner = ctk.CTkFrame(self, fg_color="transparent")
        inner.pack(fill="x", padx=SPACE_MD, pady=SPACE_MD)
        inner.grid_columnconfigure(0, weight=1)

        top = ctk.CTkFrame(inner, fg_color="transparent")
        top.grid(row=0, column=0, sticky="ew")
        top.grid_columnconfigure(0, weight=1)

        status_wrap = ctk.CTkFrame(top, fg_color="transparent")
        status_wrap.grid(row=0, column=0, sticky="e")
        self._dot = ctk.CTkFrame(
            status_wrap, width=10, height=10, corner_radius=5, fg_color=COLORS["text_muted"],
        )
        self._dot.pack(side="right", padx=(SPACE_XS, 0))
        self._status = RtlLabel(status_wrap, "زمان‌بندی خاموش است", size=15, bold=True)
        self._status.pack(side="right")

        self._phase = RtlLabel(top, "برای شروع، محدوده را تنظیم کنید", size=11, muted=True)
        self._phase.grid(row=0, column=1, sticky="w")

        target = ctk.CTkFrame(
            inner, corner_radius=RADIUS_MD, fg_color=COLORS["card_bg"],
            border_width=1, border_color=COLORS["card_border"],
        )
        target.grid(row=1, column=0, sticky="ew", pady=(SPACE_SM, 0))
        ti = ctk.CTkFrame(target, fg_color="transparent")
        ti.pack(fill="x", padx=SPACE_MD, pady=SPACE_SM)
        ti.grid_columnconfigure((0, 1, 2), weight=1)

        self._loc = self._metric(ti, 2, "محدوده", "—", "map_pin")
        self._cat = self._metric(ti, 1, "هدف استخراج", "—", "filter")
        self._interval = self._metric(ti, 0, "بازه / بعدی", "—", "timer")

        hint = ctk.CTkFrame(inner, fg_color="transparent")
        hint.grid(row=2, column=0, sticky="ew", pady=(SPACE_SM, 0))
        pack_icon(hint, "sparkles", size=14, side="right", padx=(SPACE_XS, 0))
        self._hint = RtlLabel(
            hint,
            "وقتی زمان‌بندی روشن باشد، استخراج خودکار حتی با بستن پنجره ادامه می‌یابد.",
            size=10,
            muted=True,
            wraplength=760,
        )
        self._hint.pack(side="right", fill="x", expand=True)

    def _metric(self, parent, col: int, label: str, value: str, icon: str) -> RtlLabel:
        box = ctk.CTkFrame(parent, fg_color="transparent")
        box.grid(row=0, column=col, sticky="nsew", padx=4)
        head = ctk.CTkFrame(box, fg_color="transparent")
        head.pack(fill="x")
        RtlLabel(head, label, size=9, muted=True).pack(side="right")
        pack_icon(head, icon, size=12, side="left")
        val = RtlLabel(box, value, size=12, bold=True)
        val.pack(anchor="e", pady=(4, 0))
        return val

    def update_state(
        self,
        *,
        running: bool,
        extracting: bool = False,
        location: str = "",
        target: str = "",
        interval_label: str = "",
        next_run_at: Optional[float] = None,
        remaining_seconds: Optional[int] = None,
        mode: str = "single",
        job_count: int = 0,
    ) -> None:
        if running and extracting:
            self._status.configure(text="زمان‌بندی روشن · در حال استخراج", text_color=COLORS["primary"])
            self._phase.configure(text="اجرای فعلی فعال است — لطفاً منتظر بمانید")
            self._dot.configure(fg_color=COLORS["primary"])
            self.configure(border_color=COLORS["accent_glow"], fg_color=COLORS["brand_soft"])
            self._start_pulse()
        elif running:
            rem_txt = format_duration_fa(remaining_seconds, style="words") if remaining_seconds is not None else "—"
            next_txt = format_timestamp_fa(next_run_at) if next_run_at else "—"
            self._status.configure(text="زمان‌بندی روشن است", text_color=COLORS["success"])
            self._phase.configure(text=f"اجرای بعدی: {next_txt}  ·  مانده: {rem_txt}")
            self._dot.configure(fg_color=COLORS["success"])
            self.configure(border_color=COLORS["success_border"], fg_color=COLORS["success_bg"])
            self._start_pulse()
        else:
            self._status.configure(text="زمان‌بندی خاموش است", text_color=COLORS["text_primary"])
            self._phase.configure(text="با «شروع زمان‌بندی» استخراج دوره‌ای فعال می‌شود")
            self._dot.configure(fg_color=COLORS["text_muted"])
            self.configure(border_color=COLORS["card_border"], fg_color=COLORS["surface_secondary"])
            self._stop_pulse()

        self._loc.configure(text=location or "محدوده انتخاب نشده")
        mode_txt = "گروهی" if mode == "batch" else "تکی"
        if mode == "batch" and job_count:
            mode_txt = f"گروهی · {fa_digits(job_count)} زیردسته"
        cat = target or "—"
        self._cat.configure(text=f"{mode_txt}  ·  {cat}" if cat != "—" else mode_txt)

        if running and next_run_at and not extracting:
            rem = format_duration_fa(remaining_seconds, style="words") if remaining_seconds is not None else "—"
            self._interval.configure(text=f"{interval_label or '—'}  ·  {rem}")
        elif running and extracting:
            self._interval.configure(text=f"{interval_label or '—'}  ·  اکنون")
        else:
            self._interval.configure(text=interval_label or "—")

        if mode == "batch":
            self._hint.configure(
                text="حالت گروهی: حداقل بازه ۳ ساعت است تا بار سرور و سیستم متعادل بماند.",
            )
        elif running:
            self._hint.configure(
                text="آیکن System Tray و این بنر نشان می‌دهند برنامه در پس‌زمینه فعال است.",
            )
        else:
            self._hint.configure(
                text="وقتی زمان‌بندی روشن باشد، استخراج خودکار حتی با بستن پنجره ادامه می‌یابد.",
            )

    def _start_pulse(self) -> None:
        if self._pulse_id is not None:
            return
        self._pulse_on = True
        self._pulse()

    def _stop_pulse(self) -> None:
        self._pulse_on = False
        if self._pulse_id is not None:
            try:
                self.after_cancel(self._pulse_id)
            except Exception:
                pass
            self._pulse_id = None
        try:
            self._dot.configure(fg_color=COLORS["text_muted"])
        except Exception:
            pass

    def _pulse(self) -> None:
        self._pulse_id = None
        if not self._pulse_on:
            return
        try:
            current = str(self._dot.cget("fg_color"))
            bright = COLORS["success"]
            dim = COLORS["accent_glow"] if "accent_glow" in COLORS else COLORS["primary"]
            self._dot.configure(fg_color=dim if current == bright else bright)
        except Exception:
            pass
        self._pulse_id = self.after(700, self._pulse)
