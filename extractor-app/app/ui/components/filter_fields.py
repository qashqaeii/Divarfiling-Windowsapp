"""فیلترهای پیشرفته — ردیف بازه min/max."""
from __future__ import annotations

from typing import Tuple

import customtkinter as ctk

from app.filter_utils import AMENITY_FILTER_FIELDS
from app.ui.components.cards import FieldLabel, RtlLabel
from app.ui.components.inputs import styled_entry
from app.ui.tokens import COLORS, SPACE_SM, SPACE_XS
from app.ui.typography import font


class FilterRangeRow(ctk.CTkFrame):
    """ردیف بازه عددی RTL — برچسب بالا، از/تا در یک خط."""

    def __init__(
        self,
        master,
        label: str,
        *,
        unit: str = "",
        min_placeholder: str = "از",
        max_placeholder: str = "تا",
        **kw,
    ):
        super().__init__(master, fg_color="transparent", **kw)
        title = f"{label} ({unit})" if unit else label
        FieldLabel(self, title).pack(anchor="e", pady=(0, SPACE_XS))

        row = ctk.CTkFrame(self, fg_color="transparent")
        row.pack(fill="x")
        row.grid_columnconfigure((0, 1), weight=1)

        max_wrap = ctk.CTkFrame(row, fg_color="transparent")
        max_wrap.grid(row=0, column=0, sticky="ew", padx=(0, SPACE_XS))
        RtlLabel(max_wrap, "تا", size=10, muted=True).pack(side="right", padx=(SPACE_XS, 0))
        self.max_entry = styled_entry(max_wrap, placeholder_text=max_placeholder, height=32, font=font(12))
        self.max_entry.pack(side="right", fill="x", expand=True)

        min_wrap = ctk.CTkFrame(row, fg_color="transparent")
        min_wrap.grid(row=0, column=1, sticky="ew", padx=(SPACE_XS, 0))
        RtlLabel(min_wrap, "از", size=10, muted=True).pack(side="right", padx=(SPACE_XS, 0))
        self.min_entry = styled_entry(min_wrap, placeholder_text=min_placeholder, height=32, font=font(12))
        self.min_entry.pack(side="right", fill="x", expand=True)

    def get_values(self) -> Tuple[str, str]:
        return self.min_entry.get().strip(), self.max_entry.get().strip()

    def set_values(self, min_val: str = "", max_val: str = "") -> None:
        self.min_entry.delete(0, "end")
        self.max_entry.delete(0, "end")
        if min_val:
            self.min_entry.insert(0, str(min_val))
        if max_val:
            self.max_entry.insert(0, str(max_val))

    def clear(self) -> None:
        self.set_values()


class AdvancedFiltersPanel(ctk.CTkFrame):
    """پنل فیلترهای پیشرفته — قیمت/رهن/اجاره، متراژ، سال، امکانات."""

    def __init__(self, master, app, **kw):
        super().__init__(master, fg_color="transparent", **kw)

        app._adv_filters_expanded = ctk.BooleanVar(value=False)
        adv_body = ctk.CTkFrame(self, fg_color="transparent")
        app._adv_filters_body = adv_body

        def toggle_adv() -> None:
            if app._adv_filters_expanded.get():
                adv_body.pack(fill="x", pady=(0, SPACE_SM))
                app._update_advanced_filter_visibility()
            else:
                adv_body.pack_forget()

        app._toggle_adv_filters = toggle_adv

        head = ctk.CTkFrame(self, fg_color="transparent")
        head.pack(fill="x", pady=(SPACE_SM, SPACE_XS))
        ctk.CTkSwitch(
            head,
            text="فیلترهای پیشرفته",
            variable=app._adv_filters_expanded,
            command=toggle_adv,
            font=font(11, "bold"),
            progress_color=COLORS["primary"],
            button_color=COLORS["primary_end"],
        ).pack(side="right")
        app._adv_filter_hint = RtlLabel(head, "خالی = بدون محدودیت", size=9, muted=True)
        app._adv_filter_hint.pack(side="right", padx=(SPACE_SM, 0))

        app._money_host = ctk.CTkFrame(adv_body, fg_color="transparent")
        app._money_host.pack(fill="x")

        app._price_filter_row = FilterRangeRow(
            app._money_host, "قیمت", unit="تومان",
            min_placeholder="حداقل", max_placeholder="حداکثر",
        )
        app._deposit_filter_row = FilterRangeRow(
            app._money_host, "ودیعه / رهن", unit="تومان",
            min_placeholder="حداقل", max_placeholder="حداکثر",
        )
        app._rent_filter_row = FilterRangeRow(
            app._money_host, "اجاره", unit="تومان",
            min_placeholder="حداقل", max_placeholder="حداکثر",
        )

        app._area_filter_row = FilterRangeRow(
            adv_body, "متراژ", unit="متر مربع",
            min_placeholder="حداقل", max_placeholder="حداکثر",
        )
        app._area_filter_row.pack(fill="x", pady=(0, SPACE_SM))

        app._year_filter_row = FilterRangeRow(
            adv_body, "سال ساخت", unit="شمسی",
            min_placeholder="مثلاً ۱۳۹۰", max_placeholder="مثلاً ۱۴۰۳",
        )
        app._year_filter_row.pack(fill="x", pady=(0, SPACE_SM))

        amen_row = ctk.CTkFrame(adv_body, fg_color="transparent")
        amen_row.pack(fill="x", pady=(0, SPACE_XS))
        app._amenity_filter_row = amen_row
        FieldLabel(amen_row, "امکانات").pack(anchor="e", pady=(0, SPACE_XS))
        checks = ctk.CTkFrame(amen_row, fg_color="transparent")
        checks.pack(fill="x")
        app._amenity_filter_vars: dict[str, ctk.BooleanVar] = {}
        app._amenity_filter_checks: dict[str, ctk.CTkCheckBox] = {}
        for idx, (key, label) in enumerate(AMENITY_FILTER_FIELDS):
            var = ctk.BooleanVar(value=False)
            app._amenity_filter_vars[key] = var
            cb = ctk.CTkCheckBox(
                checks,
                text=label,
                variable=var,
                command=lambda a=app: a._update_advanced_filter_visibility(),
                font=font(11),
                fg_color=COLORS["primary"],
                hover_color=COLORS["primary_hover"],
                border_color=COLORS["card_border"],
                checkmark_color=COLORS["surface"],
            )
            app._amenity_filter_checks[key] = cb
            cb.grid(row=0, column=2 - idx, sticky="e", padx=(SPACE_XS, 0))
            checks.grid_columnconfigure(2 - idx, weight=1)

        adv_body.pack_forget()

        from app.widgets import enable_entry_shortcuts

        for row in (
            app._price_filter_row,
            app._deposit_filter_row,
            app._rent_filter_row,
            app._area_filter_row,
            app._year_filter_row,
        ):
            enable_entry_shortcuts(row.min_entry)
            enable_entry_shortcuts(row.max_entry)
