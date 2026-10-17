"""دیالوگ‌های تأیید، گزارش و انتخاب سفارشی — مینیمال و حرفه‌ای."""
from __future__ import annotations

from typing import Callable, Dict, List, Optional, Set

import customtkinter as ctk

from app.batch_models import BatchJobResult, BatchRunSummary, JobStatus, UploadStatus
from app.category_jobs import JobKey
from app.constants import TRANSACTION_TYPES
from app.formatters import fa_digits
from app.ui.components import GhostButton, OutlineButton, PrimaryButton, RtlLabel
from app.ui.platform_icons import PlatformIconCache, pack_icon
from app.ui.tokens import (
    BUTTON_HEIGHT_CTA,
    CARD_RADIUS,
    COLORS,
    RADIUS_LG,
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


def _status_text(result: BatchJobResult) -> str:
    ext = {
        JobStatus.SUCCESS: "استخراج ✓",
        JobStatus.NO_RESULTS: "بدون نتیجه",
        JobStatus.FAILED: "خطای استخراج",
        JobStatus.CANCELLED: "لغو",
        JobStatus.SKIPPED: "رد شده",
        JobStatus.PENDING: "در انتظار",
        JobStatus.RUNNING: "در حال اجرا",
    }.get(result.extraction_status, result.extraction_status.value)

    if result.upload_status == UploadStatus.NOT_REQUESTED:
        upl = "آپلود: —"
    elif result.upload_status == UploadStatus.SUCCESS:
        upl = "آپلود ✓"
    elif result.upload_status == UploadStatus.FAILED:
        upl = "آپلود ✗"
    else:
        upl = f"آپلود: {result.upload_status.value}"
    return f"{ext} | {upl}"


class BatchConfirmDialog(ctk.CTkToplevel):
    """تأیید استخراج گروهی — مینیمال و حرفه‌ای."""

    def __init__(
        self,
        master,
        *,
        on_confirm: Callable[[], None],
        job_count: int = 0,
        max_items: int = 0,
        upload_enabled: bool = True,
        location: str = "",
        summary_text: str = "",
    ) -> None:
        super().__init__(master)
        self.title("تأیید استخراج")
        self.resizable(False, False)
        self.transient(master)
        self.grab_set()
        self.configure(fg_color=COLORS["card_bg"])
        self._on_confirm = on_confirm
        est = max(0, job_count * max_items)
        _center_window(self, 440, 480)

        root = ctk.CTkFrame(self, fg_color=COLORS["card_bg"])
        root.pack(fill="both", expand=True, padx=SPACE_LG, pady=SPACE_LG)

        # Hero
        icon_wrap = ctk.CTkFrame(
            root, width=64, height=64, corner_radius=20, fg_color=COLORS["brand_soft"],
        )
        icon_wrap.pack(pady=(SPACE_SM, SPACE_MD))
        icon_wrap.pack_propagate(False)
        img = PlatformIconCache.get("rocket", 28)
        if img is not None:
            lbl = ctk.CTkLabel(icon_wrap, text="", image=img, fg_color="transparent")
            lbl._icon_image = img
            lbl.place(relx=0.5, rely=0.5, anchor="center")
        else:
            ctk.CTkLabel(
                icon_wrap, text="▶", font=font(22, "bold"), text_color=COLORS["primary"],
            ).place(relx=0.5, rely=0.5, anchor="center")

        RtlLabel(root, "شروع استخراج گروهی؟", size=18, bold=True).pack(anchor="center")
        RtlLabel(
            root, "قبل از شروع، خلاصه عملیات را بررسی کنید.", size=12, muted=True,
        ).pack(anchor="center", pady=(SPACE_XS, SPACE_LG))

        if location:
            loc = ctk.CTkFrame(
                root, corner_radius=RADIUS_MD, fg_color=COLORS["surface_secondary"],
                border_width=1, border_color=COLORS["card_border"],
            )
            loc.pack(fill="x", pady=(0, SPACE_MD))
            li = ctk.CTkFrame(loc, fg_color="transparent")
            li.pack(fill="x", padx=SPACE_MD, pady=SPACE_SM)
            pack_icon(li, "map_pin", size=14, side="right", padx=(SPACE_XS, 0))
            RtlLabel(li, location, size=11, bold=True).pack(side="right")

        metrics = ctk.CTkFrame(root, fg_color="transparent")
        metrics.pack(fill="x", pady=(0, SPACE_MD))
        metrics.grid_columnconfigure((0, 1, 2), weight=1)
        self._metric(metrics, "سقف تقریبی", fa_digits(est), 0, accent=True)
        self._metric(metrics, "حداکثر هر دسته", fa_digits(max_items), 1)
        self._metric(metrics, "زیردسته", fa_digits(job_count), 2)

        # Upload status
        pill_bg = COLORS["success_bg"] if upload_enabled else COLORS["surface_secondary"]
        pill_fg = COLORS["success"] if upload_enabled else COLORS["text_muted"]
        pill_bd = COLORS["success_border"] if upload_enabled else COLORS["card_border"]
        pill = ctk.CTkFrame(
            root, corner_radius=999, fg_color=pill_bg,
            border_width=1, border_color=pill_bd,
        )
        pill.pack(pady=(0, SPACE_MD))
        pi = ctk.CTkFrame(pill, fg_color="transparent")
        pi.pack(padx=SPACE_MD, pady=6)
        pack_icon(pi, "upload", size=12, side="right", padx=(SPACE_XS, 0))
        upl = RtlLabel(
            pi,
            "آپلود خودکار فعال است" if upload_enabled else "آپلود خودکار غیرفعال است",
            size=11, bold=True,
        )
        upl.configure(text_color=pill_fg)
        upl.pack(side="right")

        hint = ctk.CTkFrame(root, corner_radius=RADIUS_MD, fg_color=COLORS["surface_secondary"])
        hint.pack(fill="x", pady=(0, SPACE_LG))
        RtlLabel(
            hint, "دسته‌ها به‌ترتیب و بدون اجرای هم‌زمان استخراج می‌شوند.",
            size=11, muted=True,
        ).pack(padx=SPACE_MD, pady=SPACE_SM)

        if summary_text and not job_count:
            RtlLabel(root, summary_text, size=11, muted=True, wraplength=380).pack(
                anchor="e", pady=(0, SPACE_MD),
            )

        actions = ctk.CTkFrame(root, fg_color="transparent")
        actions.pack(fill="x", side="bottom")
        PrimaryButton(
            actions, "شروع استخراج", self._confirm, icon_key="rocket", height=BUTTON_HEIGHT_CTA,
        ).pack(side="right", fill="x", expand=True, padx=(SPACE_SM, 0))
        OutlineButton(actions, "انصراف", self.destroy, height=BUTTON_HEIGHT_CTA, width=100).pack(side="right")

        self.bind("<Escape>", lambda _e: self.destroy())
        self.bind("<Return>", lambda _e: self._confirm())
        self.after(80, self.focus_force)

    @staticmethod
    def _metric(parent, label: str, value: str, col: int, *, accent: bool = False) -> None:
        card = ctk.CTkFrame(
            parent, corner_radius=RADIUS_MD,
            fg_color=COLORS["brand_soft"] if accent else COLORS["surface_secondary"],
            border_width=1,
            border_color=COLORS["accent_glow"] if accent else COLORS["card_border"],
        )
        card.grid(row=0, column=col, sticky="ew", padx=SPACE_XS)
        inner = ctk.CTkFrame(card, fg_color="transparent")
        inner.pack(padx=SPACE_SM, pady=SPACE_MD)
        val = RtlLabel(inner, value, size=18, bold=True)
        val.pack(anchor="center")
        if accent:
            val.configure(text_color=COLORS["primary"])
        RtlLabel(inner, label, size=10, muted=True).pack(anchor="center", pady=(4, 0))

    def _confirm(self) -> None:
        self.destroy()
        self._on_confirm()


class BatchCustomPickerDialog(ctk.CTkToplevel):
    """انتخاب سفارشی زیردسته‌ها — مینیمال، گروهی، کاربرپسند."""

    def __init__(
        self,
        master,
        *,
        initial: Set[JobKey],
        on_apply: Callable[[Set[JobKey]], None],
    ) -> None:
        super().__init__(master)
        self.title("انتخاب زیردسته‌ها")
        self.minsize(480, 560)
        self.transient(master)
        self.grab_set()
        self.configure(fg_color=COLORS["canvas_bg"])
        self._on_apply = on_apply
        self._vars: Dict[JobKey, ctk.BooleanVar] = {}
        self._group_vars: Dict[str, ctk.BooleanVar] = {}
        self._group_keys: Dict[str, List[JobKey]] = {}
        self._row_frames: Dict[JobKey, ctk.CTkFrame] = {}
        self._updating = False

        _center_window(self, 520, 640)

        root = ctk.CTkFrame(self, fg_color=COLORS["canvas_bg"])
        root.pack(fill="both", expand=True)
        root.grid_columnconfigure(0, weight=1)
        root.grid_rowconfigure(2, weight=1)

        # ── Header ──
        header = ctk.CTkFrame(root, fg_color=COLORS["card_bg"], corner_radius=0)
        header.grid(row=0, column=0, sticky="ew")
        hi = ctk.CTkFrame(header, fg_color="transparent")
        hi.pack(fill="x", padx=SPACE_LG, pady=SPACE_MD)

        titles = ctk.CTkFrame(hi, fg_color="transparent")
        titles.pack(side="right", fill="x", expand=True)
        RtlLabel(titles, "انتخاب زیردسته‌ها", size=16, bold=True).pack(anchor="e")
        RtlLabel(titles, "فقط دسته‌هایی که نیاز دارید را علامت بزنید.", size=11, muted=True).pack(
            anchor="e", pady=(2, 0),
        )

        badge = ctk.CTkFrame(
            hi, corner_radius=999, fg_color=COLORS["brand_soft"],
            border_width=1, border_color=COLORS["accent_glow"],
        )
        badge.pack(side="left")
        self._count_lbl = RtlLabel(badge, "۰", size=12, bold=True)
        self._count_lbl.configure(text_color=COLORS["primary"])
        self._count_lbl.pack(padx=SPACE_MD, pady=6)
        ctk.CTkFrame(header, height=1, fg_color=COLORS["card_border"]).pack(fill="x")

        # ── Quick tools ──
        tools = ctk.CTkFrame(root, fg_color="transparent")
        tools.grid(row=1, column=0, sticky="ew", padx=SPACE_LG, pady=(SPACE_SM, SPACE_XS))
        GhostButton(tools, "انتخاب همه", self._select_all, width=96, height=28).pack(
            side="right", padx=(SPACE_XS, 0),
        )
        GhostButton(tools, "پاک‌کردن", self._select_none, width=80, height=28).pack(side="right")

        # ── Scroll list ──
        scroll = ctk.CTkScrollableFrame(root, fg_color="transparent")
        scroll.grid(row=2, column=0, sticky="nsew", padx=SPACE_MD, pady=(0, SPACE_SM))

        for tx_name, tx_data in TRANSACTION_TYPES.items():
            subs = [
                str(s.get("label") or "")
                for s in (tx_data.get("subcategories") or [])
                if s.get("label")
            ]
            if subs:
                self._build_group(scroll, tx_name, subs, initial)

        # ── Footer ──
        footer = ctk.CTkFrame(root, fg_color=COLORS["card_bg"], corner_radius=0)
        footer.grid(row=3, column=0, sticky="ew")
        ctk.CTkFrame(footer, height=1, fg_color=COLORS["card_border"]).pack(fill="x")
        fi = ctk.CTkFrame(footer, fg_color="transparent")
        fi.pack(fill="x", padx=SPACE_LG, pady=SPACE_MD)

        self._footer_hint = RtlLabel(fi, "", size=11, muted=True)
        self._footer_hint.pack(side="right", fill="x", expand=True)
        PrimaryButton(
            fi, "اعمال انتخاب", self._apply, icon_key="sparkles", height=40, width=140,
        ).pack(side="left", padx=(SPACE_SM, 0))
        OutlineButton(fi, "انصراف", self.destroy, height=40, width=90).pack(side="left")

        self._refresh_count()
        self.bind("<Escape>", lambda _e: self.destroy())
        self.bind("<Return>", lambda _e: self._apply())
        self.after(80, self.focus_force)

    def _build_group(self, parent, tx_name: str, subs: List[str], initial: Set[JobKey]) -> None:
        group = ctk.CTkFrame(
            parent, corner_radius=RADIUS_LG, fg_color=COLORS["card_bg"],
            border_width=1, border_color=COLORS["card_border"],
        )
        group.pack(fill="x", pady=(0, SPACE_SM), padx=SPACE_XS)

        head = ctk.CTkFrame(group, fg_color=COLORS["surface_secondary"], corner_radius=0)
        head.pack(fill="x")
        hr = ctk.CTkFrame(head, fg_color="transparent")
        hr.pack(fill="x", padx=SPACE_MD, pady=SPACE_SM)

        gvar = ctk.BooleanVar(value=False)
        self._group_vars[tx_name] = gvar
        ctk.CTkCheckBox(
            hr, text="", variable=gvar, width=22,
            command=lambda t=tx_name: self._toggle_group(t),
            fg_color=COLORS["primary"], hover_color=COLORS["primary_hover"],
            checkbox_width=18, checkbox_height=18,
        ).pack(side="right")
        RtlLabel(hr, tx_name, size=12, bold=True).pack(side="right", padx=(0, SPACE_SM))
        RtlLabel(hr, f"{fa_digits(len(subs))} مورد", size=10, muted=True).pack(side="left")

        body = ctk.CTkFrame(group, fg_color="transparent")
        body.pack(fill="x", padx=SPACE_SM, pady=SPACE_SM)

        keys: List[JobKey] = []
        for label in subs:
            key: JobKey = (tx_name, label)
            keys.append(key)
            var = ctk.BooleanVar(value=key in initial)
            self._vars[key] = var
            var.trace_add("write", lambda *_a, t=tx_name: self._on_item_changed(t))

            row = ctk.CTkFrame(body, corner_radius=RADIUS_MD, fg_color=COLORS["surface_secondary"])
            row.pack(fill="x", pady=2)
            self._row_frames[key] = row
            ri = ctk.CTkFrame(row, fg_color="transparent")
            ri.pack(fill="x", padx=SPACE_SM, pady=8)

            ctk.CTkCheckBox(
                ri, text="", variable=var, width=22,
                command=self._refresh_count,
                fg_color=COLORS["primary"], hover_color=COLORS["primary_hover"],
                checkbox_width=18, checkbox_height=18,
            ).pack(side="right")
            name_lbl = RtlLabel(ri, label, size=12)
            name_lbl.pack(side="right", padx=(0, SPACE_SM), fill="x", expand=True)

            def _toggle(_e=None, v=var):
                if self._updating:
                    return
                v.set(not v.get())

            # فقط روی متن/فضای خالی — نه روی خود چک‌باکس
            name_lbl.bind("<Button-1>", _toggle)
            name_lbl.configure(cursor="hand2")
            row.configure(cursor="hand2")
            # کلیک روی پس‌زمینه ردیف (نه فرزندان چک‌باکس)
            row.bind("<Button-1>", lambda e, v=var: v.set(not v.get()) if e.widget is row else None)

        self._group_keys[tx_name] = keys
        self._sync_group_check(tx_name)

    def _paint_row(self, key: JobKey) -> None:
        row = self._row_frames.get(key)
        var = self._vars.get(key)
        if not row or not var:
            return
        if var.get():
            row.configure(
                fg_color=COLORS["brand_soft"],
                border_width=1,
                border_color=COLORS["accent_glow"],
            )
        else:
            row.configure(
                fg_color=COLORS["surface_secondary"],
                border_width=0,
                border_color=COLORS["card_border"],
            )

    def _toggle_group(self, tx_name: str) -> None:
        selected = bool(self._group_vars[tx_name].get())
        self._updating = True
        try:
            for key in self._group_keys.get(tx_name, []):
                self._vars[key].set(selected)
                self._paint_row(key)
        finally:
            self._updating = False
        self._refresh_count()

    def _on_item_changed(self, tx_name: str) -> None:
        if self._updating:
            return
        self._sync_group_check(tx_name)
        for key in self._group_keys.get(tx_name, []):
            self._paint_row(key)
        self._refresh_count()

    def _sync_group_check(self, tx_name: str) -> None:
        keys = self._group_keys.get(tx_name, [])
        if not keys:
            return
        self._group_vars[tx_name].set(all(self._vars[k].get() for k in keys))

    def _select_all(self) -> None:
        self._updating = True
        try:
            for var in self._vars.values():
                var.set(True)
            for tx in self._group_vars:
                self._group_vars[tx].set(True)
            for key in self._vars:
                self._paint_row(key)
        finally:
            self._updating = False
        self._refresh_count()

    def _select_none(self) -> None:
        self._updating = True
        try:
            for var in self._vars.values():
                var.set(False)
            for tx in self._group_vars:
                self._group_vars[tx].set(False)
            for key in self._vars:
                self._paint_row(key)
        finally:
            self._updating = False
        self._refresh_count()

    def _refresh_count(self) -> None:
        n = sum(1 for v in self._vars.values() if v.get())
        total = len(self._vars)
        self._count_lbl.configure(text=f"{fa_digits(n)} / {fa_digits(total)}")
        if n == 0:
            self._footer_hint.configure(text="هیچ زیردسته‌ای انتخاب نشده")
        elif n == total:
            self._footer_hint.configure(text="همه زیردسته‌ها انتخاب شده‌اند")
        else:
            self._footer_hint.configure(text=f"{fa_digits(n)} زیردسته برای استخراج انتخاب شد")
        for key in self._vars:
            self._paint_row(key)

    def _apply(self) -> None:
        selected = {k for k, v in self._vars.items() if v.get()}
        if not selected:
            return
        self.destroy()
        self._on_apply(selected)


class BatchReportDialog(ctk.CTkToplevel):
    def __init__(
        self,
        master,
        summary: BatchRunSummary,
        *,
        on_retry_failed: Optional[Callable[[List[BatchJobResult]], None]] = None,
    ) -> None:
        super().__init__(master)
        self.title("گزارش استخراج دسته‌ای")
        self.minsize(440, 400)
        self.transient(master)
        self.configure(fg_color=COLORS["card_bg"])
        self._summary = summary
        self._on_retry = on_retry_failed
        _center_window(self, 520, 500)

        frame = ctk.CTkFrame(self, fg_color=COLORS["card_bg"])
        frame.pack(fill="both", expand=True, padx=SPACE_LG, pady=SPACE_LG)

        ok = summary.success_count
        fail = summary.failed_count
        title = f"{fa_digits(ok)} موفق  ·  {fa_digits(fail)} نیازمند توجه"
        if summary.cancelled:
            title += "  ·  لغو شده"
        RtlLabel(frame, "گزارش استخراج گروهی", size=16, bold=True).pack(anchor="e")
        RtlLabel(frame, title, size=12, muted=True).pack(anchor="e", pady=(SPACE_XS, SPACE_MD))

        scroll = ctk.CTkScrollableFrame(
            frame, fg_color=COLORS["surface_secondary"], corner_radius=CARD_RADIUS,
        )
        scroll.pack(fill="both", expand=True, pady=(0, SPACE_MD))

        for idx, result in enumerate(summary.results, start=1):
            row = ctk.CTkFrame(scroll, fg_color=COLORS["card_bg"], corner_radius=8)
            row.pack(fill="x", pady=2, padx=2)
            inner = ctk.CTkFrame(row, fg_color="transparent")
            inner.pack(fill="x", padx=SPACE_SM, pady=SPACE_SM)
            RtlLabel(
                inner,
                f"{fa_digits(idx)}. {result.transaction_type} / {result.subcategory}",
                size=11, bold=True,
            ).pack(anchor="e")
            RtlLabel(inner, _status_text(result), size=10, muted=True).pack(anchor="e")
            if result.output_path:
                RtlLabel(inner, result.output_path, size=9, muted=True, wraplength=440).pack(anchor="e")
            if result.error_message:
                RtlLabel(inner, result.error_message, size=9, muted=True, wraplength=440).pack(anchor="e")

        btn_row = ctk.CTkFrame(frame, fg_color="transparent")
        btn_row.pack(fill="x")
        retry_jobs = [r for r in summary.results if r.is_retry_candidate]
        if retry_jobs and on_retry_failed:
            PrimaryButton(
                btn_row,
                f"تلاش مجدد ({fa_digits(len(retry_jobs))})",
                lambda: self._retry(retry_jobs),
                icon_key="rocket",
                height=40,
            ).pack(side="right", fill="x", expand=True, padx=(SPACE_SM, 0))
        OutlineButton(btn_row, "بستن", self.destroy, height=40, width=90).pack(side="right")

    def _retry(self, jobs: List[BatchJobResult]) -> None:
        self.destroy()
        if self._on_retry:
            self._on_retry(jobs)
