"""پنل انتخاب دسته‌ها برای batch extraction — فشرده با Modal سفارشی."""
from __future__ import annotations

import customtkinter as ctk
from typing import Dict, List, Set

from app.category_jobs import JobKey, all_job_keys, iter_subcategory_jobs
from app.formatters import fa_digits
from app.ui.components import AppCard, FieldLabel, OutlineButton, RtlLabel
from app.ui.components.batch_dialogs import BatchCustomPickerDialog
from app.ui.tokens import COLORS, SPACE_SM, SPACE_XS
from app.ui.typography import font

JobKeySet = Set[JobKey]

# preset: all | residential | commercial | custom
_RESIDENTIAL = {"فروش مسکونی", "اجاره مسکونی"}
_COMMERCIAL = {"فروش اداری و تجاری", "اجاره اداری و تجاری", "پروژه‌های ساخت‌وساز"}


class BatchSelectionPanel:
    def __init__(
        self,
        parent: ctk.CTkFrame,
        app,
        *,
        context: str = "extract",
        title: str = "۲. انتخاب زیردسته‌ها",
        on_change=None,
    ) -> None:
        self.app = app
        self._context = context
        self._on_change = on_change
        self._preset = ctk.StringVar(value="all")
        self._selected_keys: JobKeySet = set(all_job_keys())
        self._summary_lbl: RtlLabel | None = None
        self._estimate_lbl: RtlLabel | None = None
        self._root = ctk.CTkFrame(parent, fg_color="transparent")

        card = AppCard(self._root, title, icon_key="automation", compact=True, flat=True)
        card.pack(fill="x", pady=(0, SPACE_SM))
        body = card.body

        FieldLabel(body, "انتخاب سریع").pack(anchor="e", pady=(0, 4))
        presets = ctk.CTkFrame(body, fg_color="transparent")
        presets.pack(fill="x", pady=(0, SPACE_SM))
        presets.grid_columnconfigure((0, 1), weight=1)

        buttons = (
            ("all", "همه زیردسته‌ها"),
            ("residential", "فقط مسکونی"),
            ("commercial", "فقط تجاری"),
            ("custom", "انتخاب سفارشی"),
        )
        for i, (val, txt) in enumerate(buttons):
            btn = ctk.CTkButton(
                presets, text=txt, height=32, corner_radius=8, font=font(10, "bold"),
                command=lambda v=val: self._apply_preset(v),
                border_width=1, border_color=COLORS["card_border"],
                fg_color="transparent", text_color=COLORS["text_secondary"],
            )
            btn.grid(row=i // 2, column=1 - (i % 2), sticky="ew", padx=2, pady=2)
            setattr(self, f"_preset_btn_{val}", btn)

        self._summary_lbl = RtlLabel(body, "", size=11, bold=True)
        self._summary_lbl.pack(anchor="e", pady=(SPACE_XS, 2))
        self._summary_lbl.configure(text_color=COLORS["primary"])

        estimate = ctk.CTkFrame(body, corner_radius=0, fg_color="transparent")
        estimate.pack(fill="x", pady=(SPACE_XS, 0))
        est_inner = ctk.CTkFrame(estimate, fg_color="transparent")
        est_inner.pack(fill="x", padx=SPACE_SM, pady=SPACE_SM)
        RtlLabel(est_inner, "برآورد عملیات", size=11, bold=True).pack(anchor="e")
        self._estimate_lbl = RtlLabel(est_inner, "", size=10, muted=True)
        self._estimate_lbl.pack(anchor="e", pady=(4, 0))

        # سازگاری با کد قبلی که batch_btn را disable می‌کند
        self.batch_btn = OutlineButton(
            body, "شروع دسته‌ای", app._start_batch, icon_key="automation", height=1, width=1,
        )
        # دکمه جدا مخفی — CTA اصلی از action_bar / زمان‌بندی استفاده می‌شود
        self.batch_btn.pack_forget()

        self._paint_presets()
        self._update_summary()

    def pack(self, **kw) -> None:
        self._root.pack(**kw)

    def pack_forget(self) -> None:
        self._root.pack_forget()

    def _apply_preset(self, preset: str) -> None:
        self._preset.set(preset)
        if preset == "all":
            self._selected_keys = set(all_job_keys())
        elif preset == "residential":
            self._selected_keys = {k for k in all_job_keys() if k[0] in _RESIDENTIAL}
        elif preset == "commercial":
            self._selected_keys = {k for k in all_job_keys() if k[0] in _COMMERCIAL}
        elif preset == "custom":
            BatchCustomPickerDialog(
                self.app,
                initial=set(self._selected_keys),
                on_apply=self._on_custom_applied,
            )
            self._paint_presets()
            return
        self._paint_presets()
        self._update_summary()
        if self._on_change:
            try:
                self._on_change()
            except Exception:
                pass

    def _on_custom_applied(self, keys: JobKeySet) -> None:
        self._selected_keys = set(keys) if keys else set()
        self._preset.set("custom")
        self._paint_presets()
        self._update_summary()
        if self._on_change:
            try:
                self._on_change()
            except Exception:
                pass

    def apply_state(self, preset: str, job_keys: list | None = None) -> None:
        preset = preset if preset in ("all", "residential", "commercial", "custom") else "all"
        if preset == "custom" and job_keys:
            keys: JobKeySet = set()
            for item in job_keys:
                if isinstance(item, (list, tuple)) and len(item) >= 2:
                    keys.add((str(item[0]), str(item[1])))
            self._selected_keys = keys or set(all_job_keys())
            self._preset.set("custom")
        elif preset == "residential":
            self._selected_keys = {k for k in all_job_keys() if k[0] in _RESIDENTIAL}
            self._preset.set("residential")
        elif preset == "commercial":
            self._selected_keys = {k for k in all_job_keys() if k[0] in _COMMERCIAL}
            self._preset.set("commercial")
        else:
            self._selected_keys = set(all_job_keys())
            self._preset.set("all")
        self._paint_presets()
        self._update_summary()

    def export_state(self) -> dict:
        return {
            "batch_preset": self._preset.get(),
            "batch_job_keys": [[a, b] for a, b in sorted(self._selected_keys)],
        }

    def _paint_presets(self) -> None:
        idle = dict(
            fg_color="transparent",
            text_color=COLORS["text_secondary"],
            hover_color=COLORS["brand_soft"],
            border_width=1,
            border_color=COLORS["card_border"],
        )
        active = dict(
            fg_color=COLORS["primary"],
            text_color=COLORS["accent_text"],
            hover_color=COLORS["primary_hover"],
            border_width=0,
        )
        current = self._preset.get()
        for val in ("all", "residential", "commercial", "custom"):
            btn = getattr(self, f"_preset_btn_{val}", None)
            if btn:
                btn.configure(**(active if val == current else idle))

    def selected_job_keys(self) -> JobKeySet:
        return set(self._selected_keys)

    def selected_jobs(self) -> List[dict]:
        return iter_subcategory_jobs(selected_job_keys=self.selected_job_keys())

    def count_selected(self) -> int:
        return len(self.selected_jobs())

    def update_summary(self, max_items: int, upload_enabled: bool) -> None:
        count = self.count_selected()
        est = count * max_items
        self._summary_lbl.configure(text=f"{fa_digits(count)} زیردسته انتخاب شده")
        upload = "فعال" if upload_enabled else "غیرفعال"
        self._estimate_lbl.configure(
            text=(
                f"{fa_digits(count)} زیردسته\n"
                f"حداکثر {fa_digits(max_items)} آگهی برای هر زیردسته\n"
                f"حداکثر مجموع: {fa_digits(est)} آگهی\n"
                f"آپلود خودکار: {upload}"
            ),
        )

    def _update_summary(self) -> None:
        max_items = 100
        upload = True
        if self._context == "schedule":
            if hasattr(self.app, "sch_items_slider"):
                max_items = int(round(float(self.app.sch_items_slider.get())))
            if hasattr(self.app, "_sch_upload_var"):
                upload = bool(self.app._sch_upload_var.get())
        else:
            if hasattr(self.app, "items_slider"):
                max_items = int(round(float(self.app.items_slider.get())))
            upload = bool(getattr(self.app, "_upload_platform_var", ctk.BooleanVar(value=True)).get())
        self.update_summary(max_items, upload)
        if self._context != "schedule" and hasattr(self.app, "_refresh_start_button_label"):
            self.app._refresh_start_button_label()
        elif self._context == "schedule" and hasattr(self.app, "_update_schedule_summary"):
            try:
                self.app._update_schedule_summary()
            except Exception:
                pass

    def set_enabled(self, enabled: bool) -> None:
        state = "normal" if enabled else "disabled"
        for val in ("all", "residential", "commercial", "custom"):
            btn = getattr(self, f"_preset_btn_{val}", None)
            if btn:
                btn.configure(state=state)
        self.batch_btn.configure(state=state)
