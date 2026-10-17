"""Timeline / جدول وضعیت زیردسته‌ها — مطابق طرح."""
from __future__ import annotations

from typing import Callable, Dict, List, Optional

import customtkinter as ctk

from app.batch_models import BatchJobResult, JobStatus, UploadStatus
from app.formatters import fa_digits
from app.ui.components.buttons import GhostButton
from app.ui.components.cards import RtlLabel
from app.ui.platform_icons import pack_icon
from app.ui.tokens import CARD_RADIUS, COLORS, SPACE_MD, SPACE_SM, SPACE_XS
from app.ui.typography import font

_STATUS_META = {
    "pending": ("○", COLORS["text_muted"], "در انتظار", COLORS["surface_secondary"]),
    "running": ("●", COLORS["primary"], "در حال اجرا", COLORS["brand_soft"]),
    "done": ("◐", COLORS["info"], "در حال نهایی‌سازی", COLORS["info_bg"]),
    "success": ("✓", COLORS["success"], "موفق", COLORS["success_bg"]),
    "no_results": ("–", COLORS["warning"], "بدون نتیجه", COLORS["warning_bg"]),
    "failed": ("✗", COLORS["error"], "ناموفق", COLORS["error_bg"]),
    "cancelled": ("■", COLORS["text_muted"], "لغو", COLORS["surface_secondary"]),
    "skipped": ("○", COLORS["text_muted"], "رد شده", COLORS["surface_secondary"]),
}


class JobTimeline(ctk.CTkFrame):
    """جدول وضعیت زیردسته‌ها."""

    def __init__(self, master, *, on_open_file: Optional[Callable[[str], None]] = None, **kw):
        super().__init__(
            master,
            corner_radius=CARD_RADIUS,
            fg_color=COLORS["card_bg"],
            border_width=1,
            border_color=COLORS["card_border"],
            **kw,
        )
        self._on_open_file = on_open_file
        header = ctk.CTkFrame(self, fg_color=COLORS["section_header_bg"], corner_radius=0)
        header.pack(fill="x")
        hi = ctk.CTkFrame(header, fg_color="transparent")
        hi.pack(fill="x", padx=SPACE_MD, pady=SPACE_SM)
        pack_icon(hi, "list", size=14, side="right", padx=(SPACE_XS, 0))
        RtlLabel(hi, "وضعیت زیردسته‌ها", size=13, bold=True).pack(side="right")

        # column headers
        cols = ctk.CTkFrame(self, fg_color=COLORS["surface_secondary"], corner_radius=10)
        cols.pack(fill="x", padx=SPACE_SM, pady=(0, SPACE_XS))
        crow = ctk.CTkFrame(cols, fg_color="transparent")
        crow.pack(fill="x", padx=SPACE_SM, pady=SPACE_XS)
        RtlLabel(crow, "وضعیت", size=9, muted=True).pack(side="right", padx=(0, 24))
        RtlLabel(crow, "دسته / زیردسته", size=9, muted=True).pack(side="right", expand=True)
        RtlLabel(crow, "تعداد", size=9, muted=True).pack(side="left", padx=(24, 0))
        RtlLabel(crow, "فایل", size=9, muted=True).pack(side="left")

        self._scroll = ctk.CTkScrollableFrame(self, fg_color="transparent", height=180)
        self._scroll.pack(fill="both", expand=True, padx=SPACE_SM, pady=(0, SPACE_SM))
        self._rows: Dict[str, ctk.CTkFrame] = {}
        self._paths: Dict[str, str] = {}
        self._empty = RtlLabel(
            self._scroll, "پس از شروع، وضعیت هر زیردسته اینجا نمایش داده می‌شود.", size=11, muted=True,
        )
        self._empty.pack(anchor="e", pady=SPACE_SM)

    def clear(self) -> None:
        for row in self._rows.values():
            row.destroy()
        self._rows.clear()
        self._paths.clear()
        if self._empty.winfo_exists():
            self._empty.pack(anchor="e", pady=SPACE_SM)

    def set_jobs(self, jobs: List[dict]) -> None:
        self.clear()
        if self._empty.winfo_exists():
            self._empty.pack_forget()
        for job in jobs:
            key = self._key(job["transaction_type"], job["subcategory"])
            self._rows[key] = self._make_row(
                job["transaction_type"], job["subcategory"], status="pending", count=0,
            )

    def set_running(self, index: int, label: str) -> None:
        keys = list(self._rows.keys())
        terminal = {"success", "no_results", "failed", "cancelled", "skipped"}
        for i, key in enumerate(keys):
            row = self._rows[key]
            state = getattr(row, "_state", "pending")
            if state in terminal:
                continue
            if i == index:
                self._paint_row(row, status="running")
            elif i > index and state == "pending":
                self._paint_row(row, status="pending")

    def apply_job_result(self, result: BatchJobResult) -> None:
        """به‌روزرسانی وضعیت نهایی یک زیردسته بلافاصله پس از اتمام job."""
        if self._empty.winfo_exists():
            self._empty.pack_forget()
        status, detail = self._result_status(result)
        key = self._key(result.transaction_type, result.subcategory)
        if result.output_path:
            self._paths[key] = result.output_path
        if key not in self._rows:
            self._rows[key] = self._make_row(
                result.transaction_type,
                result.subcategory,
                status=status,
                count=result.extracted_count,
                path=result.output_path,
            )
        else:
            self._paint_row(
                self._rows[key],
                status=status,
                count=result.extracted_count,
                path=result.output_path,
                detail=detail,
            )

    def apply_results(self, results: List[BatchJobResult]) -> None:
        if self._empty.winfo_exists():
            self._empty.pack_forget()
        for result in results:
            self.apply_job_result(result)

    def _make_row(
        self, tx: str, sub: str, *, status: str, count: int = 0, path: Optional[str] = None,
    ) -> ctk.CTkFrame:
        row = ctk.CTkFrame(self._scroll, fg_color="transparent")
        row.pack(fill="x", pady=2)
        inner = ctk.CTkFrame(
            row, fg_color=COLORS["card_bg"], corner_radius=8,
            border_width=1, border_color=COLORS["card_border_soft"],
        )
        inner.pack(fill="x")
        body = ctk.CTkFrame(inner, fg_color="transparent")
        body.pack(fill="x", padx=SPACE_SM, pady=7)

        # status badge (right)
        badge = ctk.CTkFrame(body, corner_radius=999, fg_color=COLORS["surface_secondary"], width=86, height=28)
        badge.pack(side="right", padx=(SPACE_SM, 0))
        badge.pack_propagate(False)
        badge_inner = ctk.CTkFrame(badge, fg_color="transparent")
        badge_inner.pack(expand=True, fill="both")
        icon_lbl = ctk.CTkLabel(badge_inner, text="○", font=font(11, "bold"), width=14)
        icon_lbl.pack(side="right")
        status_lbl = RtlLabel(badge_inner, "", size=10, bold=True)
        status_lbl.pack(side="right", padx=(0, 2))

        short_tx = tx.replace(" اداری و تجاری", "")
        name_lbl = RtlLabel(body, f"{short_tx} / {sub}", size=11, bold=True)
        name_lbl.pack(side="right", fill="x", expand=True, padx=(SPACE_SM, 0))

        action = GhostButton(body, "مشاهده", lambda: None, icon_key="folder", width=74, height=28)
        action.pack(side="left")
        action.configure(state="disabled")

        count_lbl = RtlLabel(body, "—", size=10, muted=True)
        count_lbl.pack(side="left", padx=(SPACE_SM, SPACE_MD))

        row._badge = badge  # type: ignore[attr-defined]
        row._icon_lbl = icon_lbl  # type: ignore[attr-defined]
        row._status_lbl = status_lbl  # type: ignore[attr-defined]
        row._count_lbl = count_lbl  # type: ignore[attr-defined]
        row._action = action  # type: ignore[attr-defined]
        row._path = path or ""  # type: ignore[attr-defined]
        row._state = status  # type: ignore[attr-defined]
        self._paint_row(row, status=status, count=count, path=path)
        return row

    def _paint_row(
        self, row: ctk.CTkFrame, *, status: str, count: Optional[int] = None,
        upload: str = "", detail: str = "", path: Optional[str] = None,
    ) -> None:
        icon, color, label, bg = _STATUS_META.get(status, _STATUS_META["pending"])
        row._state = status
        row._icon_lbl.configure(text=icon, text_color=color)
        row._status_lbl.configure(text=detail or label, text_color=color)
        row._badge.configure(fg_color=bg)
        if count is not None:
            row._count_lbl.configure(
                text=f"{fa_digits(count)} آگهی" if count > 0 else "—",
            )
        if path:
            row._path = path
            row._action.configure(
                state="normal",
                command=lambda p=path: self._open(p),
            )
        elif status == "success" and row._path:
            row._action.configure(state="normal", command=lambda p=row._path: self._open(p))
        elif status in ("pending", "running"):
            row._action.configure(state="disabled")

    def _open(self, path: str) -> None:
        if self._on_open_file and path:
            self._on_open_file(path)
        elif path:
            import os
            import subprocess
            import sys
            folder = os.path.dirname(path) or path
            if sys.platform == "win32":
                os.startfile(folder)
            elif sys.platform == "darwin":
                subprocess.run(["open", folder], check=False)
            else:
                subprocess.run(["xdg-open", folder], check=False)

    @staticmethod
    def _key(tx: str, sub: str) -> str:
        return f"{tx}||{sub}"

    @staticmethod
    def _result_status(result: BatchJobResult) -> tuple[str, str]:
        if result.extraction_status == JobStatus.SUCCESS:
            if result.upload_status == UploadStatus.FAILED:
                return "failed", "آپلود ناموفق"
            return "success", ""
        if result.extraction_status == JobStatus.NO_RESULTS:
            return "no_results", ""
        if result.extraction_status == JobStatus.FAILED:
            return "failed", ""
        if result.extraction_status == JobStatus.CANCELLED:
            return "cancelled", ""
        if result.extraction_status == JobStatus.SKIPPED:
            return "skipped", ""
        return result.extraction_status.value, ""

    @staticmethod
    def _upload_label(status: UploadStatus) -> str:
        if status == UploadStatus.SUCCESS:
            return "آپلود ✓"
        if status == UploadStatus.FAILED:
            return "آپلود ✗"
        return ""
