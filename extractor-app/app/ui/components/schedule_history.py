"""تاریخچه و گزارش استخراج‌های زمان‌بندی‌شده."""
from __future__ import annotations

import os
from typing import Any, Callable, Dict, List, Optional

import customtkinter as ctk

from app.formatters import fa_digits, format_datetime_fa, format_duration_fa
from app.ui.components.buttons import GhostButton, OutlineButton
from app.ui.components.cards import RtlLabel, StatusBadge
from app.ui.platform_icons import pack_icon
from app.ui.tokens import CARD_RADIUS, COLORS, RADIUS_MD, SPACE_LG, SPACE_MD, SPACE_SM, SPACE_XS
from app.ui.typography import font

_STATUS_META = {
    "success": ("موفق", "success"),
    "no_results": ("بدون نتیجه", "warning"),
    "failed": ("ناموفق", "error"),
    "cancelled": ("لغو شده", "muted"),
    "skipped": ("به تعویق", "info"),
}


class ScheduleHistoryPanel(ctk.CTkFrame):
    """لیست گزارش‌های اجراهای زمان‌بندی‌شده."""

    def __init__(
        self,
        master,
        *,
        on_open_output: Optional[Callable[[str], None]] = None,
        on_clear: Optional[Callable[[], None]] = None,
        on_refresh: Optional[Callable[[], None]] = None,
        **kw,
    ):
        super().__init__(
            master,
            corner_radius=CARD_RADIUS,
            fg_color=COLORS["card_bg"],
            border_width=1,
            border_color=COLORS["card_border"],
            **kw,
        )
        self._on_open_output = on_open_output
        self._rows: List[ctk.CTkFrame] = []
        self._empty: Optional[ctk.CTkFrame] = None

        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", padx=SPACE_MD, pady=(SPACE_MD, SPACE_SM))
        header.grid_columnconfigure(0, weight=1)

        title_row = ctk.CTkFrame(header, fg_color="transparent")
        title_row.grid(row=0, column=0, sticky="e")
        pack_icon(title_row, "list", size=14, side="right", padx=(SPACE_XS, 0))
        RtlLabel(title_row, "تاریخچه استخراج‌ها", size=13, bold=True).pack(side="right")
        self._subtitle = RtlLabel(
            header, "گزارش کامل اجراهای زمان‌بندی‌شده", size=10, muted=True,
        )
        self._subtitle.grid(row=1, column=0, sticky="e", pady=(2, 0))

        actions = ctk.CTkFrame(header, fg_color="transparent")
        actions.grid(row=0, column=1, rowspan=2, sticky="w")
        if on_refresh:
            GhostButton(
                actions, "بروزرسانی", on_refresh, icon_key="refresh", width=96, height=30,
            ).pack(side="left", padx=(0, SPACE_XS))
        if on_clear:
            OutlineButton(
                actions, "پاک کردن", on_clear, icon_key="clear", width=96, height=30,
            ).pack(side="left")

        cols = ctk.CTkFrame(
            self, fg_color=COLORS["surface_secondary"], corner_radius=RADIUS_MD,
        )
        cols.pack(fill="x", padx=SPACE_MD, pady=(0, SPACE_XS))
        crow = ctk.CTkFrame(cols, fg_color="transparent")
        crow.pack(fill="x", padx=SPACE_SM, pady=SPACE_XS)
        RtlLabel(crow, "وضعیت", size=9, muted=True).pack(side="right", padx=(0, SPACE_SM))
        RtlLabel(crow, "زمان اجرا", size=9, muted=True).pack(side="right", padx=(0, SPACE_MD))
        RtlLabel(crow, "محدوده / دسته", size=9, muted=True).pack(side="right", expand=True)
        RtlLabel(crow, "نتیجه", size=9, muted=True).pack(side="left", padx=(SPACE_MD, 0))
        RtlLabel(crow, "مدت", size=9, muted=True).pack(side="left", padx=(SPACE_MD, 0))
        RtlLabel(crow, "خروجی", size=9, muted=True).pack(side="left")

        self._scroll = ctk.CTkScrollableFrame(self, fg_color="transparent", height=220)
        self._scroll.pack(fill="both", expand=True, padx=SPACE_SM, pady=(0, SPACE_MD))
        self._show_empty()

    def set_runs(self, runs: List[Dict[str, Any]]) -> None:
        for row in self._rows:
            try:
                row.destroy()
            except Exception:
                pass
        self._rows.clear()
        if self._empty is not None:
            try:
                self._empty.destroy()
            except Exception:
                pass
            self._empty = None

        total = len(runs)
        self._subtitle.configure(
            text=(
                f"{fa_digits(total)} گزارش ثبت‌شده"
                if total
                else "هنوز اجرای زمان‌بندی‌شده‌ای ثبت نشده است"
            ),
        )
        if not runs:
            self._show_empty()
            return

        for run in runs:
            self._rows.append(self._make_row(run))

    def _show_empty(self) -> None:
        self._empty = ctk.CTkFrame(
            self._scroll,
            fg_color=COLORS["surface_secondary"],
            corner_radius=RADIUS_MD,
            border_width=1,
            border_color=COLORS["card_border"],
        )
        self._empty.pack(fill="x", pady=SPACE_SM)
        inner = ctk.CTkFrame(self._empty, fg_color="transparent")
        inner.pack(fill="x", padx=SPACE_MD, pady=SPACE_LG)
        RtlLabel(inner, "تاریخچه خالی است", size=13, bold=True).pack(anchor="e")
        RtlLabel(
            inner,
            "پس از شروع زمان‌بندی، گزارش هر اجرا با جزئیات کامل اینجا نمایش داده می‌شود.",
            size=11,
            muted=True,
            wraplength=640,
        ).pack(anchor="e", pady=(SPACE_XS, 0))

    def _make_row(self, run: Dict[str, Any]) -> ctk.CTkFrame:
        status = str(run.get("status") or "muted")
        label, tone = _STATUS_META.get(status, ("نامشخص", "muted"))

        row = ctk.CTkFrame(
            self._scroll,
            fg_color=COLORS["surface_secondary"],
            corner_radius=RADIUS_MD,
            border_width=1,
            border_color=COLORS["card_border"],
        )
        row.pack(fill="x", pady=(0, SPACE_XS))
        inner = ctk.CTkFrame(row, fg_color="transparent")
        inner.pack(fill="x", padx=SPACE_SM, pady=SPACE_SM)

        StatusBadge(inner, label, tone=tone).pack(side="right", padx=(SPACE_SM, 0))

        when = format_datetime_fa(str(run.get("finished_at") or run.get("started_at") or ""))
        RtlLabel(inner, when, size=11, bold=True).pack(side="right", padx=(0, SPACE_MD))

        place_parts = [
            p for p in (
                str(run.get("province") or "").strip(),
                str(run.get("city") or "").strip(),
                str(run.get("district") or "").strip(),
            ) if p and p != "—"
        ]
        place = " / ".join(place_parts) if place_parts else "—"
        mode = str(run.get("mode") or "single")
        jobs_total = int(run.get("jobs_total") or 0)
        if mode == "batch" or jobs_total > 1:
            ok_jobs = int(run.get("jobs_success") or 0)
            fail_jobs = int(run.get("jobs_failed") or 0)
            category = f"گروهی · {fa_digits(jobs_total or ok_jobs + fail_jobs)} زیردسته"
            if ok_jobs or fail_jobs:
                category = f"{category} (✓{fa_digits(ok_jobs)} / ⚠{fa_digits(fail_jobs)})"
        else:
            category = " — ".join(
                p for p in (
                    str(run.get("transaction_type") or "").strip(),
                    str(run.get("subcategory") or "").strip(),
                ) if p
            ) or "—"
        info = ctk.CTkFrame(inner, fg_color="transparent")
        info.pack(side="right", fill="x", expand=True)
        RtlLabel(info, place, size=11, bold=True).pack(anchor="e")
        RtlLabel(info, category, size=10, muted=True).pack(anchor="e")
        query = str(run.get("search_query") or "").strip()
        if query and mode != "batch" and jobs_total <= 1:
            RtlLabel(info, f"جستجو: {query}", size=9, muted=True).pack(anchor="e")
        err = str(run.get("error_message") or "").strip()
        show_err = bool(err) and (
            status in ("failed", "skipped")
            or (status == "success" and (mode == "batch" or jobs_total > 1) and int(run.get("jobs_failed") or 0) > 0)
        )
        if show_err:
            RtlLabel(info, err[:90], size=9, muted=True).pack(anchor="e")

        ok = int(run.get("ok_count") or 0)
        total = int(run.get("total_posts") or 0)
        if status == "success":
            result_txt = f"{fa_digits(ok)} آگهی"
            if total and total != ok:
                result_txt = f"{fa_digits(ok)} از {fa_digits(total)}"
        elif status == "no_results":
            result_txt = "بدون آگهی"
        elif status == "skipped":
            result_txt = "تعویق"
        elif status == "cancelled":
            result_txt = "لغو"
        else:
            result_txt = "خطا"
        RtlLabel(inner, result_txt, size=11, bold=True).pack(side="left", padx=(SPACE_MD, 0))

        duration_secs = int(run.get("duration_seconds") or 0)
        duration = format_duration_fa(duration_secs, style="words") if duration_secs > 0 else "—"
        RtlLabel(inner, duration, size=10, muted=True).pack(side="left", padx=(SPACE_MD, 0))

        output_path = str(run.get("output_path") or "").strip()
        if output_path and os.path.isfile(output_path) and self._on_open_output:
            GhostButton(
                inner,
                "باز کردن",
                lambda p=output_path: self._on_open_output(p),
                icon_key="folder",
                width=88,
                height=28,
            ).pack(side="left")
        else:
            RtlLabel(inner, "—", size=10, muted=True).pack(side="left", padx=(8, 0))

        return row
