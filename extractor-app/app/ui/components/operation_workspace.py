"""فضای اصلی عملیات — مطابق داشبورد طرح."""
from __future__ import annotations

from typing import Callable, List, Optional

import customtkinter as ctk

from app.batch_models import BatchJobResult, BatchRunSummary, JobStatus, UploadStatus
from app.formatters import fa_digits
from app.ui.components.buttons import GhostButton, OutlineButton, PrimaryButton
from app.ui.components.cards import RtlLabel, StatusBadge
from app.ui.components.empty_state import EmptyState
from app.ui.components.job_timeline import JobTimeline
from app.ui.components.log_viewer import LiveLogViewer
from app.ui.components.progress import OverallProgressCard, ProgressCard
from app.ui.components.stat_card import StatCard
from app.ui.platform_icons import pack_icon
from app.ui.tokens import CARD_RADIUS, COLORS, CONTENT_GAP, SPACE_MD, SPACE_SM, SPACE_XS


class SummaryInfoCard(ctk.CTkFrame):
    """کارت خلاصه کوچک بالای داشبورد."""

    def __init__(self, master, label: str, value: str = "—", *, icon_key: str = "", **kw):
        super().__init__(
            master,
            corner_radius=CARD_RADIUS,
            fg_color=COLORS["card_bg"],
            border_width=1,
            border_color=COLORS["card_border"],
            height=72,
            **kw,
        )
        inner = ctk.CTkFrame(self, fg_color="transparent")
        inner.pack(fill="both", expand=True, padx=SPACE_MD, pady=SPACE_SM)
        top = ctk.CTkFrame(inner, fg_color="transparent")
        top.pack(fill="x")
        RtlLabel(top, label, size=10, muted=True).pack(side="right")
        if icon_key:
            pack_icon(top, icon_key, size=14, side="left")
        self._val = RtlLabel(inner, value, size=13, bold=True)
        self._val.pack(anchor="e", pady=(SPACE_SM, 0))

    def set_value(self, text: str) -> None:
        self._val.configure(text=text)


class OperationWorkspace(ctk.CTkFrame):
    """workspace عملیات استخراج."""

    def __init__(
        self,
        master,
        *,
        on_copy_log: Optional[Callable[[str], None]] = None,
        on_open_folder: Optional[Callable[[], None]] = None,
        on_open_platform: Optional[Callable[[], None]] = None,
        on_retry_failed: Optional[Callable[[List], None]] = None,
        **kw,
    ):
        super().__init__(master, fg_color="transparent", **kw)
        self._on_open_folder = on_open_folder
        self._on_open_platform = on_open_platform
        self._on_retry_failed = on_retry_failed
        self._state = "idle"

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        self.summary = ctk.CTkFrame(self, fg_color="transparent")
        self.summary.grid(row=0, column=0, sticky="ew", pady=(0, SPACE_SM))
        self.summary.grid_columnconfigure((0, 1, 2, 3), weight=1)

        self.card_limit = SummaryInfoCard(self.summary, "تعداد برای هر زیردسته", "—", icon_key="database")
        self.card_limit.grid(row=0, column=0, sticky="ew", padx=(0, SPACE_XS))
        self.card_subs = SummaryInfoCard(self.summary, "زیردسته‌های انتخاب‌شده", "—", icon_key="filter")
        self.card_subs.grid(row=0, column=1, sticky="ew", padx=SPACE_XS)
        self.card_mode = SummaryInfoCard(self.summary, "نوع استخراج", "تکی", icon_key="automation")
        self.card_mode.grid(row=0, column=2, sticky="ew", padx=SPACE_XS)
        self.card_area = SummaryInfoCard(self.summary, "محدوده انتخاب‌شده", "—", icon_key="map_pin")
        self.card_area.grid(row=0, column=3, sticky="ew", padx=(SPACE_XS, 0))

        self.chip_province = self.card_area
        self.chip_city = self.card_area
        self.chip_category = self.card_subs
        self.chip_mode = self.card_mode
        self.op_status_badge = StatusBadge(self, "آماده", tone="muted", icon_key="timer")
        self.op_status_badge.grid_remove()

        self._stack = ctk.CTkFrame(self, fg_color="transparent")
        self._stack.grid(row=1, column=0, sticky="nsew")
        self._stack.grid_columnconfigure(0, weight=1)
        self._stack.grid_rowconfigure(0, weight=1)

        self._idle = EmptyState(
            self._stack,
            icon_key="database",
            title="آماده شروع استخراج",
            description="محدوده و دسته موردنظر را از پنل سمت راست انتخاب کنید.\nپس از شروع، وضعیت عملیات در این بخش نمایش داده می‌شود.",
        )
        self._idle.grid(row=0, column=0, sticky="nsew")

        self._active = ctk.CTkFrame(self._stack, fg_color="transparent")
        self._active.grid_columnconfigure(0, weight=1)
        self._active.grid_rowconfigure(2, weight=1)

        prog_row = ctk.CTkFrame(self._active, fg_color="transparent")
        prog_row.grid(row=0, column=0, sticky="ew", pady=(0, SPACE_SM))
        prog_row.grid_columnconfigure(0, weight=1)

        self.progress_card = ProgressCard(prog_row)
        self.progress_card.grid(row=0, column=0, sticky="ew", padx=(0, SPACE_SM))
        self.overall_card = OverallProgressCard(prog_row)
        self.overall_card.grid(row=0, column=1, sticky="ns")

        stats = ctk.CTkFrame(self._active, fg_color="transparent")
        stats.grid(row=1, column=0, sticky="ew", pady=(0, SPACE_SM))
        stats.grid_columnconfigure((0, 1, 2), weight=1)
        self.stat_card_ok = StatCard(stats, "زمان گذشته", "—", icon_key="timer")
        self.stat_card_ok.grid(row=0, column=0, sticky="ew", padx=(0, SPACE_XS))
        self.stat_card_done = StatCard(stats, "موفق", "—", accent=True, icon_key="sparkles")
        self.stat_card_done.grid(row=0, column=1, sticky="ew", padx=SPACE_XS)
        self.stat_card_total = StatCard(stats, "استخراج‌شده", "—", icon_key="database")
        self.stat_card_total.grid(row=0, column=2, sticky="ew", padx=(SPACE_XS, 0))

        self._mid = ctk.CTkFrame(self._active, fg_color="transparent")
        self._mid.grid(row=2, column=0, sticky="nsew")
        self._mid.grid_columnconfigure(0, weight=3)
        self._mid.grid_columnconfigure(1, weight=2)
        self._mid.grid_rowconfigure(0, weight=1)

        self.timeline = JobTimeline(self._mid)
        self.timeline.grid(row=0, column=0, sticky="nsew", padx=(0, CONTENT_GAP // 2))

        # parent = _stack تا بتوان با in_ بین _mid و _completed_body جابه‌جا شد
        self.log_viewer = LiveLogViewer(self._stack, on_copy=on_copy_log)
        self.log_viewer.grid(
            row=0, column=1, sticky="nsew", padx=(CONTENT_GAP // 2, 0), in_=self._mid,
        )
        self.log_viewer.prepare_line_tags()

        self._completed = ctk.CTkFrame(
            self._stack, corner_radius=CARD_RADIUS, fg_color=COLORS["card_bg"],
            border_width=1, border_color=COLORS["card_border"],
        )
        self._completed_body = ctk.CTkFrame(self._completed, fg_color="transparent")
        self._completed_body.pack(fill="both", expand=True, padx=SPACE_MD, pady=SPACE_MD)
        self._complete_title = RtlLabel(self._completed_body, "استخراج به پایان رسید", size=16, bold=True)
        self._complete_title.pack(anchor="e")
        self._complete_summary = RtlLabel(self._completed_body, "", size=12, muted=True)
        self._complete_summary.pack(anchor="e", pady=(SPACE_SM, SPACE_MD))

        actions = ctk.CTkFrame(self._completed_body, fg_color="transparent")
        actions.pack(fill="x", pady=(0, SPACE_MD))
        PrimaryButton(
            actions, "بازکردن پوشه خروجی",
            lambda: self._on_open_folder and self._on_open_folder(),
            icon_key="folder", height=36, width=160,
        ).pack(side="right", padx=(SPACE_XS, 0))
        self._platform_btn = OutlineButton(
            actions, "مشاهده در پلتفرم",
            lambda: self._on_open_platform and self._on_open_platform(),
            icon_key="upload", height=36, width=140,
        )
        self._platform_btn.pack(side="right", padx=(SPACE_XS, 0))
        self._retry_btn = OutlineButton(
            actions, "تلاش مجدد موارد ناموفق",
            self._do_retry, icon_key="rocket", height=36, width=180,
        )
        GhostButton(actions, "بازگشت به آماده", self.show_idle, height=36, width=120).pack(side="right")

        self._complete_list = ctk.CTkScrollableFrame(
            self._completed_body, fg_color=COLORS["surface_secondary"], corner_radius=8, height=180,
        )
        self._retry_jobs: List = []

        path_card = ctk.CTkFrame(
            self, corner_radius=CARD_RADIUS, fg_color=COLORS["brand_soft"],
            border_width=1, border_color=COLORS["accent_glow"],
        )
        path_card.grid(row=2, column=0, sticky="ew", pady=(SPACE_SM, 0))
        path_row = ctk.CTkFrame(path_card, fg_color="transparent")
        path_row.pack(fill="x", padx=SPACE_MD, pady=(SPACE_XS, SPACE_SM))
        pack_icon(path_row, "folder", size=14, side="right", padx=(SPACE_XS, 0))
        self.path_preview = RtlLabel(path_row, "", size=10, muted=True, wraplength=700)
        self.path_preview.pack(side="right", fill="x", expand=True, anchor="e")

        self.show_idle()

    @property
    def progress(self):
        return self.progress_card.progress

    @property
    def progress_percent(self):
        return self.progress_card.progress_percent

    @property
    def current_task_lbl(self):
        return self.progress_card.current_task_lbl

    @property
    def scrape_time_info(self):
        return self.progress_card.scrape_time_info

    @property
    def stat_done(self):
        return self.progress_card.stat_done

    @property
    def stat_total(self):
        return self.progress_card.stat_total

    @property
    def stat_success(self):
        return self.progress_card.stat_success

    @property
    def log_box(self):
        return self.log_viewer.widget

    def _place_log_in_mid(self, *, batch: bool) -> None:
        """گزارش زنده را به ناحیهٔ اجرای فعال برمی‌گرداند."""
        try:
            self.log_viewer.pack_forget()
        except Exception:
            pass
        try:
            self.log_viewer.grid_forget()
        except Exception:
            pass
        if batch:
            self.log_viewer.grid(
                row=0, column=1, sticky="nsew", padx=(CONTENT_GAP // 2, 0), in_=self._mid,
            )
        else:
            self.log_viewer.grid(
                row=0, column=0, columnspan=2, sticky="nsew", padx=0, in_=self._mid,
            )

    def _place_log_in_completed(self) -> None:
        """گزارش زنده را در صفحهٔ پایان استخراج نگه می‌دارد (تکی)."""
        try:
            self.log_viewer.grid_forget()
        except Exception:
            pass
        try:
            self.log_viewer.pack_forget()
        except Exception:
            pass
        self.log_viewer.pack(
            in_=self._completed_body, fill="both", expand=True,
        )

    def show_idle(self) -> None:
        self._state = "idle"
        self._place_log_in_mid(batch=False)
        self._idle.grid(row=0, column=0, sticky="nsew")
        self._active.grid_forget()
        self._completed.grid_forget()
        self.op_status_badge.configure_text("آماده", tone="muted")
        self.overall_card.set_progress(0, 0)

    def show_running(self, *, batch: bool = False) -> None:
        self._state = "running"
        self._idle.grid_forget()
        self._completed.grid_forget()
        self._active.grid(row=0, column=0, sticky="nsew")
        self.op_status_badge.configure_text("در حال اجرا", tone="brand")
        if batch:
            self.overall_card.grid()
            self.timeline.grid(row=0, column=0, sticky="nsew", padx=(0, CONTENT_GAP // 2))
            self._place_log_in_mid(batch=True)
        else:
            self.overall_card.grid_remove()
            self.timeline.grid_remove()
            self._place_log_in_mid(batch=False)

    def show_completed(
        self,
        summary: Optional[BatchRunSummary] = None,
        *,
        single_ok: bool = False,
        outcome: str = "idle",
        show_platform_link: bool = False,
    ) -> None:
        self._state = "completed"
        self._idle.grid_forget()
        self._active.grid_forget()
        self._completed.grid(row=0, column=0, sticky="nsew")
        badge_tone = "success"
        badge_text = "پایان یافت"
        if outcome == "failed":
            badge_tone = "error"
            badge_text = "خطا"
        elif outcome in ("no_results", "upload_failed"):
            badge_tone = "warning"
        elif outcome == "cancelled":
            badge_tone = "muted"
        self.op_status_badge.configure_text(badge_text, tone=badge_tone)
        if hasattr(self, "_platform_btn"):
            if show_platform_link:
                self._platform_btn.pack(side="right", padx=(SPACE_XS, 0))
            else:
                self._platform_btn.pack_forget()

        for child in self._complete_list.winfo_children():
            child.destroy()

        if summary is not None:
            try:
                self.log_viewer.pack_forget()
            except Exception:
                pass
            self._place_log_in_mid(batch=True)
            self._complete_list.pack(fill="both", expand=True)
            total_ads = sum(r.extracted_count for r in summary.results)
            self._complete_title.configure(text="استخراج گروهی به پایان رسید")
            self._complete_summary.configure(
                text=(
                    f"{fa_digits(summary.success_count)} دسته موفق  ·  "
                    f"{fa_digits(summary.failed_count)} نیازمند توجه  ·  "
                    f"{fa_digits(total_ads)} آگهی استخراج شد"
                ),
            )
            self._retry_jobs = [r for r in summary.results if r.is_retry_candidate]
            if self._retry_jobs:
                self._retry_btn.pack(side="right", padx=(SPACE_XS, 0))
            else:
                self._retry_btn.pack_forget()
            for result in summary.results:
                self._add_result_row(result)
            self.timeline.apply_results(summary.results)
        else:
            # استخراج تکی: لیست خالی گروهی را مخفی کن و گزارش زنده را نگه دار
            try:
                self._complete_list.pack_forget()
            except Exception:
                pass
            title_map = {
                "success": "استخراج با موفقیت پایان یافت",
                "upload_failed": "فایل خروجی ساخته شد — آپلود ناموفق",
                "no_results": "آگهی منطبق با فیلتر یافت نشد",
                "failed": "خطا در ساخت خروجی / استخراج",
                "cancelled": "عملیات لغو شد",
            }
            self._complete_title.configure(
                text=title_map.get(outcome, "استخراج به پایان رسید" if single_ok else "عملیات پایان یافت")
            )
            summary_map = {
                "success": "نتیجه در گزارش زنده و پوشه خروجی قابل مشاهده است.",
                "upload_failed": "فایل محلی ذخیره شده است؛ آپلود به پلتفرم انجام نشد.",
                "no_results": "پس از فیلترها آگهی‌ای برای export باقی نماند.",
                "failed": "جزئیات در گزارش زنده و فایل لاگ محلی ثبت شده است.",
                "cancelled": "می‌توانید دوباره استخراج را آغاز کنید.",
            }
            self._complete_summary.configure(
                text=summary_map.get(outcome, "نتیجه در گزارش زنده و پوشه خروجی قابل مشاهده است.")
            )
            self._retry_btn.pack_forget()
            self._retry_jobs = []
            self._place_log_in_completed()

    def set_batch_overall(self, completed: int, total: int, current_frac: float = 0.0) -> None:
        self.overall_card.set_progress(completed, total, current_frac)

    def _add_result_row(self, result: BatchJobResult) -> None:
        row = ctk.CTkFrame(self._complete_list, fg_color=COLORS["card_bg"], corner_radius=8)
        row.pack(fill="x", pady=2, padx=2)
        inner = ctk.CTkFrame(row, fg_color="transparent")
        inner.pack(fill="x", padx=SPACE_SM, pady=SPACE_XS)
        RtlLabel(inner, f"{result.transaction_type} / {result.subcategory}", size=11, bold=True).pack(anchor="e")
        ext = {
            JobStatus.SUCCESS: "استخراج موفق",
            JobStatus.NO_RESULTS: "بدون نتیجه",
            JobStatus.FAILED: "خطای استخراج",
            JobStatus.CANCELLED: "لغو",
        }.get(result.extraction_status, result.extraction_status.value)
        upl = ""
        if result.upload_status == UploadStatus.SUCCESS:
            upl = " · آپلود موفق"
        elif result.upload_status == UploadStatus.FAILED:
            upl = " · آپلود ناموفق"
        count = f" · {fa_digits(result.extracted_count)} آگهی" if result.extracted_count else ""
        RtlLabel(inner, f"{ext}{upl}{count}", size=10, muted=True).pack(anchor="e")

    def _do_retry(self) -> None:
        if self._on_retry_failed and self._retry_jobs:
            self._on_retry_failed(self._retry_jobs)
