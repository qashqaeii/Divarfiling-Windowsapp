"""انتخاب تعداد آگهی — preset + اسلایدر سفارشی ۱ تا ۵۰۰."""
from __future__ import annotations

from typing import Callable, Optional

import customtkinter as ctk

from app.constants import MAX_EXTRACTION_ITEMS
from app.formatters import fa_digits
from app.ui.components.cards import FieldLabel, RtlLabel
from app.ui.components.inputs import styled_entry
from app.ui.components.select_box import apply_combobox_rtl, styled_combobox
from app.ui.tokens import CARD_RADIUS, COLORS, RADIUS_MD, SPACE_MD, SPACE_SM, SPACE_XS
from app.ui.typography import font
from app.widgets import enable_entry_shortcuts

PRESET_VALUES = (100, 250, 500)
PRESET_LABELS = ("۱۰۰", "۲۵۰", "۵۰۰", "سفارشی")


class ItemsCountPicker(ctk.CTkFrame):
    """انتخابگر تعداد — سازگار با API اسلایدر (.get / .set)."""

    def __init__(
        self,
        master,
        *,
        initial: int = 100,
        max_items: int = MAX_EXTRACTION_ITEMS,
        on_change: Optional[Callable[[float], None]] = None,
        label: str = "تعداد برای هر زیردسته",
        unit: str = "آگهی",
        **kw,
    ):
        super().__init__(master, fg_color="transparent", **kw)
        self._max = max(1, int(max_items))
        self._on_change = on_change
        self._value = max(1, min(self._max, int(initial)))
        self._suppress = False
        self._custom_mode = False

        FieldLabel(self, label).pack(anchor="e", pady=(0, 4))

        row = ctk.CTkFrame(self, fg_color="transparent")
        row.pack(fill="x")
        row.grid_columnconfigure(0, weight=1)

        self._unit_lbl = RtlLabel(row, unit, size=11, muted=True)
        self._unit_lbl.grid(row=0, column=1, sticky="e", padx=(SPACE_SM, 0))

        self._combo = styled_combobox(
            row, values=list(PRESET_LABELS), state="readonly", height=34, font=font(12),
        )
        self._combo.grid(row=0, column=0, sticky="ew")
        self._combo.configure(command=self._on_combo)
        apply_combobox_rtl(self._combo)

        # ── پنل سفارشی: اسلایدر حرفه‌ای ۱…۵۰۰ ──────────────────────────
        self._custom_row = ctk.CTkFrame(
            self, corner_radius=CARD_RADIUS, fg_color=COLORS["card_bg"],
            border_width=1, border_color=COLORS["card_border"],
        )
        panel = ctk.CTkFrame(self._custom_row, fg_color="transparent")
        panel.pack(fill="x", padx=SPACE_SM, pady=SPACE_SM)

        # مقدار بزرگ + ورودی دقیق
        value_row = ctk.CTkFrame(panel, fg_color="transparent")
        value_row.pack(fill="x", pady=(0, SPACE_SM))

        entry_wrap = ctk.CTkFrame(
            value_row, corner_radius=RADIUS_MD, fg_color=COLORS["surface_secondary"],
            border_width=1, border_color=COLORS["input_border"], width=72, height=36,
        )
        entry_wrap.pack(side="left")
        entry_wrap.pack_propagate(False)
        self._custom_entry = styled_entry(
            entry_wrap, height=32, font=font(13, "bold"), justify="center",
        )
        self._custom_entry.pack(fill="both", expand=True, padx=2, pady=2)
        enable_entry_shortcuts(self._custom_entry)
        self._custom_entry.bind("<KeyRelease>", lambda _e: self._on_entry())
        self._custom_entry.bind("<FocusOut>", lambda _e: self._on_entry(commit=True))
        self._custom_entry.bind("<Return>", lambda _e: self._on_entry(commit=True))

        RtlLabel(value_row, "آگهی", size=11, muted=True).pack(side="left", padx=(SPACE_XS, 0))

        self._value_display = RtlLabel(value_row, fa_digits(self._value), size=22, bold=True)
        self._value_display.configure(text_color=COLORS["primary"])
        self._value_display.pack(side="right")

        # اسلایدر
        self._slider = ctk.CTkSlider(
            panel,
            from_=1,
            to=self._max,
            number_of_steps=max(1, self._max - 1),
            command=self._on_slider,
            height=18,
            progress_color=COLORS["primary"],
            button_color=COLORS["primary_end"],
            button_hover_color=COLORS["primary_hover"],
            fg_color=COLORS["progress_track"],
        )
        self._slider.pack(fill="x", pady=(0, SPACE_XS))
        self._slider.set(float(self._value))

        # مقیاس
        scale = ctk.CTkFrame(panel, fg_color="transparent")
        scale.pack(fill="x")
        scale.grid_columnconfigure((0, 1, 2, 3), weight=1)
        markers = (1, min(100, self._max), min(250, self._max), self._max)
        # RTL: بزرگ‌ترین سمت چپ
        for col, m in enumerate(markers):
            RtlLabel(scale, fa_digits(m), size=9, muted=True).grid(
                row=0, column=3 - col, sticky="e" if col == 0 else ("w" if col == 3 else ""),
            )

        # میان‌برهای سریع روی اسلایدر
        chips = ctk.CTkFrame(panel, fg_color="transparent")
        chips.pack(fill="x", pady=(SPACE_SM, 0))
        chips.grid_columnconfigure((0, 1, 2, 3, 4), weight=1)
        quick = (1, 50, 100, 250, self._max)
        for col, q in enumerate(quick):
            btn = ctk.CTkButton(
                chips, text=fa_digits(q), height=26, corner_radius=8,
                font=font(10, "bold"),
                fg_color="transparent",
                text_color=COLORS["text_secondary"],
                hover_color=COLORS["brand_soft"],
                border_width=1, border_color=COLORS["card_border"],
                command=lambda v=q: self._jump_to(v),
            )
            btn.grid(row=0, column=4 - col, sticky="ew", padx=1)

        hint = RtlLabel(
            panel, f"با اهرم یا ورود مستقیم — بازه ۱ تا {fa_digits(self._max)}",
            size=9, muted=True,
        )
        hint.pack(anchor="e", pady=(SPACE_XS, 0))

        self.set(float(self._value))

    def get(self) -> float:
        return float(self._value)

    def set(self, value: float) -> None:
        val = max(1, min(self._max, int(round(float(value)))))
        self._value = val
        self._suppress = True
        try:
            if not self._custom_mode and val in PRESET_VALUES:
                idx = PRESET_VALUES.index(val)
                self._combo.set(PRESET_LABELS[idx])
                self._hide_custom()
            else:
                if self._custom_mode or val not in PRESET_VALUES:
                    self._custom_mode = True
                    self._combo.set("سفارشی")
                    self._show_custom()
                    self._sync_custom_widgets(val)
                else:
                    idx = PRESET_VALUES.index(val)
                    self._combo.set(PRESET_LABELS[idx])
                    self._hide_custom()
        finally:
            self._suppress = False
        self._notify()

    def _show_custom(self) -> None:
        if not self._custom_row.winfo_ismapped():
            self._custom_row.pack(fill="x", pady=(SPACE_SM, 0))

    def _hide_custom(self) -> None:
        self._custom_mode = False
        if self._custom_row.winfo_ismapped():
            self._custom_row.pack_forget()

    def _sync_custom_widgets(self, val: int) -> None:
        self._value_display.configure(text=fa_digits(val))
        try:
            self._slider.set(float(val))
        except Exception:
            pass
        current = self._custom_entry.get().strip()
        if current != str(val):
            self._custom_entry.delete(0, "end")
            self._custom_entry.insert(0, str(val))

    def _on_combo(self, choice: str) -> None:
        if self._suppress:
            return
        if choice == "سفارشی":
            self._custom_mode = True
            self._show_custom()
            self._sync_custom_widgets(self._value)
            self._notify()
            return
        self._hide_custom()
        try:
            idx = PRESET_LABELS.index(choice)
            self._value = PRESET_VALUES[idx]
        except ValueError:
            self._value = 100
        self._notify()

    def _on_slider(self, value: float) -> None:
        if self._suppress:
            return
        val = max(1, min(self._max, int(round(float(value)))))
        self._value = val
        self._suppress = True
        try:
            self._value_display.configure(text=fa_digits(val))
            self._custom_entry.delete(0, "end")
            self._custom_entry.insert(0, str(val))
        finally:
            self._suppress = False
        self._notify()

    def _on_entry(self, commit: bool = False) -> None:
        if self._suppress:
            return
        raw = self._custom_entry.get().strip().translate(
            str.maketrans("۰۱۲۳۴۵۶۷۸۹", "0123456789"),
        )
        if not raw:
            return
        try:
            val = int(raw)
        except ValueError:
            return
        val = max(1, min(self._max, val))
        self._value = val
        self._suppress = True
        try:
            self._value_display.configure(text=fa_digits(val))
            self._slider.set(float(val))
            if commit and self._custom_entry.get().strip() != str(val):
                self._custom_entry.delete(0, "end")
                self._custom_entry.insert(0, str(val))
        finally:
            self._suppress = False
        self._notify()

    def _jump_to(self, value: int) -> None:
        val = max(1, min(self._max, int(value)))
        self._custom_mode = True
        self._value = val
        self._suppress = True
        try:
            self._combo.set("سفارشی")
            self._show_custom()
            self._sync_custom_widgets(val)
        finally:
            self._suppress = False
        self._notify()

    def _notify(self) -> None:
        if self._on_change:
            self._on_change(float(self._value))
