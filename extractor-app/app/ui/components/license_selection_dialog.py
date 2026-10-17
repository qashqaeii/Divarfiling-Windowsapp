"""دیالوگ انتخاب لایسنس — وقتی چند لایسنس مجاز وجود دارد."""
from __future__ import annotations

from typing import Any, Callable, Dict, List, Optional

import customtkinter as ctk

from app.formatters import fa_digits, format_expiry_fa
from app.ui.components import OutlineButton, PrimaryButton, RtlLabel
from app.ui.tokens import CARD_RADIUS, COLORS, SPACE_MD, SPACE_SM, SPACE_XS
from app.ui.typography import font


class LicenseSelectionDialog(ctk.CTkToplevel):
    def __init__(
        self,
        master,
        licenses: List[Dict[str, Any]],
        on_select: Callable[[int], None],
        on_cancel: Optional[Callable[[], None]] = None,
    ) -> None:
        super().__init__(master)
        self.title("انتخاب لایسنس")
        self.resizable(False, False)
        self.configure(fg_color=COLORS["app_bg"])
        self._on_select = on_select
        self._on_cancel = on_cancel
        self._selected_id: Optional[int] = None
        self._vars: Dict[int, ctk.StringVar] = {}

        self.transient(master)
        self.grab_set()

        wrap = ctk.CTkFrame(self, fg_color="transparent")
        wrap.pack(fill="both", expand=True, padx=SPACE_MD, pady=SPACE_MD)

        RtlLabel(
            wrap, "کدام لایسنس را روی این سیستم فعال کنید؟",
            size=14, bold=True,
        ).pack(anchor="e", pady=(0, SPACE_SM))

        for item in licenses:
            self._vars[item["license_id"]] = ctk.StringVar(value="")
            row = self._license_row(wrap, item)
            row.pack(fill="x", pady=(0, SPACE_XS))

        btns = ctk.CTkFrame(wrap, fg_color="transparent")
        btns.pack(fill="x", pady=(SPACE_SM, 0))
        OutlineButton(btns, "انصراف", self._cancel, width=90, height=34).pack(side="left")
        PrimaryButton(btns, "ادامه", self._confirm, width=100, height=34).pack(side="right")

        self.update_idletasks()
        w, h = 460, min(420, 160 + len(licenses) * 88)
        x = master.winfo_rootx() + (master.winfo_width() - w) // 2
        y = master.winfo_rooty() + (master.winfo_height() - h) // 2
        self.geometry(f"{w}x{h}+{x}+{y}")

    def _license_row(self, parent, item: Dict[str, Any]) -> ctk.CTkFrame:
        frame = ctk.CTkFrame(
            parent, corner_radius=CARD_RADIUS, fg_color=COLORS["card_bg"],
            border_width=1, border_color=COLORS["card_border"],
        )
        inner = ctk.CTkFrame(frame, fg_color="transparent")
        inner.pack(fill="x", padx=SPACE_SM, pady=SPACE_SM)

        lid = item["license_id"]
        rb = ctk.CTkRadioButton(
            inner,
            text="",
            variable=self._vars[lid],
            value=str(lid),
            width=20,
            command=lambda i=lid: self._pick(i),
        )
        rb.pack(side="right", padx=(SPACE_XS, 0))

        col = ctk.CTkFrame(inner, fg_color="transparent")
        col.pack(side="right", fill="x", expand=True)
        plan = item.get("plan_name") or "—"
        key_short = item.get("key_short") or "—"
        slots = item.get("slots_available", 0)
        RtlLabel(col, f"پلن {plan} · …{key_short}", size=12, bold=True).pack(anchor="e")
        meta = f"اسلات آزاد: {fa_digits(slots)} · انقضا: {format_expiry_fa(item.get('expires_at'))}"
        RtlLabel(col, meta, size=10, muted=True).pack(anchor="e", pady=(2, 0))
        return frame

    def _pick(self, license_id: int) -> None:
        self._selected_id = license_id
        for lid, var in self._vars.items():
            var.set(str(lid) if lid == license_id else "")

    def _confirm(self) -> None:
        if self._selected_id is None:
            for lid, var in self._vars.items():
                if var.get() == str(lid):
                    self._selected_id = lid
                    break
        if self._selected_id is None:
            return
        self.grab_release()
        self.destroy()
        self._on_select(self._selected_id)

    def _cancel(self) -> None:
        self.grab_release()
        self.destroy()
        if self._on_cancel:
            self._on_cancel()
