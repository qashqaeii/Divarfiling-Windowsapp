"""صفحه زمان‌بندی استخراج خودکار — داشبورد مینیمال و تاریخچه گزارش‌ها."""
from __future__ import annotations

import customtkinter as ctk

from app.constants import SCHEDULER_MAX_ITEMS, TRANSACTION_TYPES
from app.formatters import fa_digits
from app.scheduler import hours_to_interval_label, scheduler_interval_labels
from app.ui.components import (
    AppCard,
    FieldLabel,
    GhostButton,
    OutlineButton,
    PageHero,
    PrimaryButton,
    RtlLabel,
    styled_combobox,
    styled_entry,
    apply_combobox_rtl,
    style_scrollable,
)
from app.ui.components.batch_selection import BatchSelectionPanel
from app.ui.components.mode_selector import ExtractionModeSelector
from app.ui.components.schedule_history import ScheduleHistoryPanel
from app.ui.components.schedule_live_banner import ScheduleLiveBanner
from app.ui.tokens import BUTTON_HEIGHT_CTA, CARD_RADIUS, COLORS, RADIUS_MD, SPACE_MD, SPACE_SM, SPACE_XS
from app.ui.typography import font
from app.widgets import enable_entry_shortcuts


def build_schedule_page(app) -> ctk.CTkFrame:
    """ساخت صفحه زمان‌بندی — sch_* attrs روی app."""
    page = ctk.CTkFrame(app._pages_container, fg_color="transparent")
    page.grid_columnconfigure(0, weight=1)
    page.grid_rowconfigure(1, weight=1)

    head = ctk.CTkFrame(page, fg_color="transparent")
    head.grid(row=0, column=0, sticky="ew", pady=(0, SPACE_SM))
    head.grid_columnconfigure(0, weight=1)

    PageHero(
        head, "زمان‌بندی", eyebrow="اتوماسیون",
        subtitle="استخراج دوره‌ای تکی یا گروهی — وضعیت زنده و تاریخچه کامل",
        icon_key="automation",
    ).grid(row=0, column=0, sticky="ew")

    scroll = ctk.CTkScrollableFrame(page, fg_color="transparent", corner_radius=0)
    scroll.grid(row=1, column=0, sticky="nsew")
    style_scrollable(scroll)

    body = ctk.CTkFrame(scroll, fg_color="transparent")
    body.pack(fill="both", expand=True)
    body.grid_columnconfigure((0, 1), weight=1)

    saved_sch = app._settings.get("scheduler") or {}
    saved_mode = saved_sch.get("mode") if saved_sch.get("mode") in ("single", "batch") else "single"

    # ── بنر وضعیت زنده ──────────────────────────────────────────────
    app._sch_live_banner = ScheduleLiveBanner(body)
    app._sch_live_banner.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, SPACE_MD))

    # ── داشبورد وضعیت ───────────────────────────────────────────────
    dash = ctk.CTkFrame(
        body, corner_radius=CARD_RADIUS, fg_color=COLORS["card_bg"],
        border_width=1, border_color=COLORS["card_border"],
    )
    dash.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(0, SPACE_MD))
    di = ctk.CTkFrame(dash, fg_color="transparent")
    di.pack(fill="x", padx=SPACE_MD, pady=SPACE_MD)
    di.grid_columnconfigure((0, 1, 2, 3, 4), weight=1)

    app._sch_stat_status = _dash_metric(di, 4, "وضعیت", "متوقف", tone="muted")
    app._sch_stat_next = _dash_metric(di, 3, "اجرای بعدی", "—", tone="muted")
    app._sch_stat_remain = _dash_metric(di, 2, "مانده تا اجرا", "—", tone="muted")
    app._sch_stat_last = _dash_metric(di, 1, "آخرین اجرا", "—", tone="muted")
    app._sch_stat_count = _dash_metric(di, 0, "کل گزارش‌ها", "۰", tone="brand")
    app.sch_status_lbl = app._sch_stat_status

    # ── ستون راست: محدوده و دسته ────────────────────────────────────
    loc_card = AppCard(body, "محدوده و هدف استخراج", icon_key="map_pin", compact=True)
    loc_card.grid(row=2, column=1, sticky="nsew", padx=(SPACE_SM, 0), pady=(0, SPACE_SM))
    lb = loc_card.body

    copy_row = ctk.CTkFrame(lb, fg_color="transparent")
    copy_row.pack(fill="x", pady=(0, SPACE_SM))
    OutlineButton(
        copy_row, "کپی از تب استخراج", app._copy_extraction_to_scheduler,
        icon_key="copy", height=32,
    ).pack(side="right")
    RtlLabel(
        copy_row, "محدوده و دستهٔ فعلی استخراج را اینجا بیاورید",
        size=10, muted=True,
    ).pack(side="right", padx=(0, SPACE_SM))

    FieldLabel(lb, "حالت زمان‌بندی").pack(anchor="e", pady=(0, 4))
    app._sch_mode_selector = ExtractionModeSelector(
        lb, initial=saved_mode, on_change=app._on_sch_mode_changed,
    )
    app._sch_mode_selector.pack(fill="x", pady=(0, SPACE_SM))
    app._sch_mode = saved_mode

    for label, attr in (
        ("استان", "sch_province_cb"),
        ("شهر", "sch_city_cb"),
        ("منطقه", "sch_district_cb"),
    ):
        FieldLabel(lb, label).pack(anchor="e", pady=(SPACE_XS, 2))
        cb = styled_combobox(lb, state="disabled")
        cb.pack(fill="x", pady=(0, SPACE_SM))
        setattr(app, attr, cb)

    app.sch_province_cb.configure(command=app._on_sch_province_changed)
    app.sch_city_cb.configure(command=app._on_sch_city_changed)
    app.sch_district_cb.configure(values=["—"])

    app._sch_single_fields = ctk.CTkFrame(lb, fg_color="transparent")
    FieldLabel(app._sch_single_fields, "نوع معامله").pack(anchor="e", pady=(SPACE_XS, 2))
    app.sch_transaction_cb = styled_combobox(
        app._sch_single_fields, values=list(TRANSACTION_TYPES.keys()), state="readonly",
        command=app._on_sch_transaction_changed,
    )
    app.sch_transaction_cb.pack(fill="x", pady=(0, SPACE_SM))
    FieldLabel(app._sch_single_fields, "زیردسته").pack(anchor="e", pady=(0, 4))
    app.sch_subcategory_cb = styled_combobox(app._sch_single_fields, state="readonly")
    app.sch_subcategory_cb.pack(fill="x", pady=(0, SPACE_SM))

    FieldLabel(app._sch_single_fields, "جستجوی متنی (اختیاری)").pack(anchor="e", pady=(SPACE_XS, 2))
    app.sch_search_entry = styled_entry(
        app._sch_single_fields, placeholder_text="مثلاً پارکینگ، نوساز…", height=34,
    )
    app.sch_search_entry.pack(fill="x", pady=(0, SPACE_SM))
    enable_entry_shortcuts(app.sch_search_entry)

    app._sch_batch_host = ctk.CTkFrame(lb, fg_color="transparent")
    app._sch_batch_panel = BatchSelectionPanel(
        app._sch_batch_host,
        app,
        context="schedule",
        title="زیردسته‌های گروهی",
        on_change=app._update_schedule_summary,
    )
    app._sch_batch_panel.pack(fill="x")
    if saved_sch.get("batch_preset") or saved_sch.get("batch_job_keys"):
        app._sch_batch_panel.apply_state(
            str(saved_sch.get("batch_preset") or "all"),
            saved_sch.get("batch_job_keys") or [],
        )

    # ── ستون چپ: تکرار و خروجی ──────────────────────────────────────
    repeat_card = AppCard(body, "تکرار و خروجی", icon_key="schedule", compact=True)
    repeat_card.grid(row=2, column=0, sticky="nsew", padx=(0, SPACE_SM), pady=(0, SPACE_SM))
    rb = repeat_card.body

    app._sch_expanded = ctk.BooleanVar(value=True)
    app._toggle_sch = lambda: None

    FieldLabel(rb, "بازه تکرار").pack(anchor="e", pady=(0, 4))
    app.sch_interval_cb = styled_combobox(
        rb,
        values=scheduler_interval_labels(mode=saved_mode),
        state="readonly",
        height=34,
        font=font(13),
        command=lambda *_: app._update_schedule_summary(),
    )
    app.sch_interval_cb.pack(fill="x", pady=(0, SPACE_XS))
    app.sch_interval_cb.set(
        hours_to_interval_label(
            float(saved_sch.get("interval_hours", 6)),
            mode=saved_mode,
        ),
    )
    app._sch_interval_hint = RtlLabel(
        rb,
        "در حالت گروهی حداقل بازه ۳ ساعت است.",
        size=9,
        muted=True,
    )
    app._sch_interval_hint.pack(anchor="e", pady=(0, SPACE_SM))

    interval_chips = ctk.CTkFrame(rb, fg_color="transparent")
    interval_chips.pack(fill="x", pady=(0, SPACE_SM))
    interval_chips.grid_columnconfigure((0, 1, 2, 3), weight=1)
    app._sch_interval_chips = interval_chips
    app._sch_interval_chip_btns = {}
    for col, (hours, short) in enumerate((
        (1.0, "۱ ساعت"), (6.0, "۶ ساعت"), (24.0, "روزانه"), (168.0, "هفتگی"),
    )):
        btn = ctk.CTkButton(
            interval_chips, text=short, height=28, corner_radius=8, font=font(10, "bold"),
            fg_color="transparent", text_color=COLORS["text_secondary"],
            hover_color=COLORS["brand_soft"], border_width=1, border_color=COLORS["card_border"],
            command=lambda h=hours: app._set_sch_interval_hours(h),
        )
        btn.grid(row=0, column=3 - col, sticky="ew", padx=1)
        app._sch_interval_chip_btns[hours] = btn

    FieldLabel(rb, "تعداد آگهی در هر اجرا").pack(anchor="e", pady=(SPACE_XS, 4))
    items_head = ctk.CTkFrame(rb, fg_color="transparent")
    items_head.pack(fill="x")
    app.sch_items_value_lbl = RtlLabel(items_head, "۱۰۰ آگهی", size=16, bold=True)
    app.sch_items_value_lbl.configure(text_color=COLORS["primary"])
    app.sch_items_value_lbl.pack(side="right")
    RtlLabel(items_head, "۰ = بدون استخراج", size=9, muted=True).pack(side="left")

    sch_items_default = float(saved_sch.get("max_items", 100))
    sch_items_default = max(0, min(SCHEDULER_MAX_ITEMS, sch_items_default))
    app.sch_items_slider = ctk.CTkSlider(
        rb, from_=0, to=SCHEDULER_MAX_ITEMS, number_of_steps=SCHEDULER_MAX_ITEMS,
        command=app._on_sch_items_changed, height=18,
        progress_color=COLORS["primary"], button_color=COLORS["primary_end"],
        button_hover_color=COLORS["primary_hover"], fg_color=COLORS["progress_track"],
    )
    app.sch_items_slider.set(sch_items_default)
    app.sch_items_slider.pack(fill="x", pady=(SPACE_XS, SPACE_XS))

    items_scale = ctk.CTkFrame(rb, fg_color="transparent")
    items_scale.pack(fill="x", pady=(0, SPACE_XS))
    items_scale.grid_columnconfigure((0, 1, 2, 3), weight=1)
    for col, m in enumerate((0, 100, 250, SCHEDULER_MAX_ITEMS)):
        RtlLabel(items_scale, fa_digits(m), size=9, muted=True).grid(
            row=0, column=3 - col, sticky="e" if col == 0 else ("w" if col == 3 else ""),
        )

    quick_items = ctk.CTkFrame(rb, fg_color="transparent")
    quick_items.pack(fill="x", pady=(0, SPACE_SM))
    quick_items.grid_columnconfigure((0, 1, 2, 3, 4), weight=1)
    for col, q in enumerate((0, 50, 100, 250, SCHEDULER_MAX_ITEMS)):
        label = "بدون" if q == 0 else fa_digits(q)
        ctk.CTkButton(
            quick_items, text=label, height=26, corner_radius=8, font=font(10, "bold"),
            fg_color="transparent", text_color=COLORS["text_secondary"],
            hover_color=COLORS["brand_soft"], border_width=1, border_color=COLORS["card_border"],
            command=lambda v=q: app._set_sch_items(v),
        ).grid(row=0, column=4 - col, sticky="ew", padx=1)

    app._on_sch_items_changed(sch_items_default)

    FieldLabel(rb, "فرمت خروجی").pack(anchor="e", pady=(SPACE_XS, 4))
    saved_fmt = saved_sch.get("output_format") or "excel"
    app._sch_output_format = ctk.StringVar(value=saved_fmt if saved_fmt in ("excel", "csv", "json") else "excel")
    fmt_row = ctk.CTkFrame(rb, fg_color="transparent")
    fmt_row.pack(fill="x", pady=(0, SPACE_SM))
    fmt_row.grid_columnconfigure((0, 1, 2), weight=1)
    app._sch_format_btns = {}

    def _paint_sch_fmt() -> None:
        cur = app._sch_output_format.get()
        for val, btn in app._sch_format_btns.items():
            if val == cur:
                btn.configure(
                    fg_color=COLORS["primary"], text_color=COLORS["accent_text"],
                    hover_color=COLORS["primary_hover"],
                )
            else:
                btn.configure(
                    fg_color="transparent", text_color=COLORS["text_secondary"],
                    hover_color=COLORS["brand_soft"],
                )
        app._update_schedule_summary()

    def _set_sch_fmt(val: str) -> None:
        app._sch_output_format.set(val)
        _paint_sch_fmt()

    for col, (val, txt) in enumerate((("excel", "Excel"), ("csv", "CSV"), ("json", "JSON"))):
        btn = ctk.CTkButton(
            fmt_row, text=txt, height=30, corner_radius=RADIUS_MD, font=font(11, "bold"),
            command=lambda v=val: _set_sch_fmt(v),
        )
        btn.grid(row=0, column=2 - col, sticky="ew", padx=1)
        app._sch_format_btns[val] = btn
    _paint_sch_fmt()

    FieldLabel(rb, "نوع آگهی‌دهنده").pack(anchor="e", pady=(0, 4))
    app._sch_advertiser_filter = ctk.StringVar(value="all")
    sch_adv = ctk.CTkFrame(rb, fg_color="transparent")
    sch_adv.pack(fill="x", pady=(0, SPACE_SM))
    sch_adv.grid_columnconfigure((0, 1), weight=1)
    from app.filter_utils import ADVERTISER_FILTER_OPTIONS

    for idx, (val, txt) in enumerate(ADVERTISER_FILTER_OPTIONS):
        r, c = divmod(idx, 2)
        ctk.CTkRadioButton(
            sch_adv, text=txt, variable=app._sch_advertiser_filter, value=val,
            font=font(11, "bold"),
            fg_color=COLORS["primary"], hover_color=COLORS["primary_hover"],
            command=app._update_schedule_summary,
        ).grid(row=r, column=1 - c, sticky="ew", padx=4, pady=2)

    opts = ctk.CTkFrame(rb, fg_color="transparent")
    opts.pack(fill="x", pady=(0, SPACE_SM))
    opts.grid_columnconfigure((0, 1), weight=1)
    app._sch_upload_var = ctk.BooleanVar(
        value=bool(saved_sch.get("upload_to_platform", True)),
    )
    app.sch_upload_cb = ctk.CTkCheckBox(
        opts, text="آپلود خودکار", variable=app._sch_upload_var, font=font(11),
        fg_color=COLORS["primary"], hover_color=COLORS["primary_hover"],
        command=app._update_schedule_summary,
    )
    app.sch_upload_cb.grid(row=0, column=1, sticky="e")
    app.sch_download_images_cb = ctk.CTkCheckBox(
        opts, text="دانلود تصاویر", font=font(11),
        fg_color=COLORS["primary"], hover_color=COLORS["primary_hover"],
        command=app._update_schedule_summary,
    )
    app.sch_download_images_cb.grid(row=0, column=0, sticky="w")

    app._sch_run_now_var = ctk.BooleanVar(value=True)
    app.sch_run_now_cb = ctk.CTkCheckBox(
        rb, text="اجرای فوری هنگام شروع زمان‌بندی", variable=app._sch_run_now_var,
        font=font(11), fg_color=COLORS["primary"], hover_color=COLORS["primary_hover"],
    )
    app.sch_run_now_cb.pack(anchor="e", pady=(0, SPACE_SM))

    # ── خلاصه فشرده ─────────────────────────────────────────────────
    summary_card = AppCard(body, "خلاصه برنامه", icon_key="list", compact=True)
    summary_card.grid(row=3, column=0, columnspan=2, sticky="ew", pady=(0, SPACE_SM))
    app._sch_summary_lbl = RtlLabel(
        summary_card.body, "محدوده و بازه را انتخاب کنید.", size=11, muted=True, wraplength=780,
    )
    app._sch_summary_lbl.pack(anchor="e")
    RtlLabel(
        summary_card.body,
        "زمان‌بندی فقط وقتی اجرا می‌شود که استخراج دستی در حال اجرا نباشد.",
        size=9, muted=True, wraplength=780,
    ).pack(anchor="e", pady=(SPACE_XS, 0))

    # ── تاریخچه گزارش‌ها ────────────────────────────────────────────
    app._sch_history = ScheduleHistoryPanel(
        body,
        on_open_output=app._open_schedule_output,
        on_clear=app._clear_scheduler_history,
        on_refresh=app._refresh_scheduler_history,
    )
    app._sch_history.grid(row=4, column=0, columnspan=2, sticky="nsew", pady=(0, SPACE_SM))

    # ── فوتر کنترل ──────────────────────────────────────────────────
    footer = ctk.CTkFrame(
        page, corner_radius=CARD_RADIUS, fg_color=COLORS["card_bg"],
        border_width=1, border_color=COLORS["card_border"],
    )
    footer.grid(row=2, column=0, sticky="ew", pady=(SPACE_SM, 0))
    fi = ctk.CTkFrame(footer, fg_color="transparent")
    fi.pack(fill="x", padx=SPACE_MD, pady=SPACE_SM)

    status_pill = ctk.CTkFrame(
        fi, corner_radius=999, fg_color=COLORS["surface_secondary"],
        border_width=1, border_color=COLORS["card_border"],
    )
    status_pill.pack(side="right", padx=(0, SPACE_MD))
    pill_inner = ctk.CTkFrame(status_pill, fg_color="transparent")
    pill_inner.pack(padx=SPACE_SM, pady=6)
    app._sch_footer_dot = ctk.CTkFrame(
        pill_inner, width=8, height=8, corner_radius=4, fg_color=COLORS["text_muted"],
    )
    app._sch_footer_dot.pack(side="right", padx=(SPACE_XS, 0))
    app._sch_footer_status = RtlLabel(pill_inner, "آماده شروع", size=11, bold=True)
    app._sch_footer_status.pack(side="right")
    app._sch_footer_target = RtlLabel(fi, "", size=10, muted=True)
    app._sch_footer_target.pack(side="right", padx=(0, SPACE_SM))

    sch_btn_row = ctk.CTkFrame(fi, fg_color="transparent")
    sch_btn_row.pack(side="left")
    GhostButton(
        sch_btn_row, "ذخیره", app._scheduler_save, icon_key="save", width=100, height=BUTTON_HEIGHT_CTA,
    ).pack(side="left", padx=(0, SPACE_XS))
    OutlineButton(
        sch_btn_row, "توقف", app._scheduler_stop, icon_key="stop", width=100, height=BUTTON_HEIGHT_CTA,
    ).pack(side="left", padx=(0, SPACE_XS))
    PrimaryButton(
        sch_btn_row, "شروع زمان‌بندی", app._scheduler_play,
        icon_key="rocket", width=150, height=BUTTON_HEIGHT_CTA,
    ).pack(side="left")

    for cb in (
        app.sch_province_cb, app.sch_city_cb, app.sch_district_cb,
        app.sch_transaction_cb, app.sch_subcategory_cb, app.sch_interval_cb,
    ):
        apply_combobox_rtl(cb)

    app.after(30, lambda: app._on_sch_mode_changed(saved_mode))
    app.after(100, app._update_schedule_summary)
    app.after(150, app._refresh_scheduler_history)
    app.after(200, app._refresh_scheduler_live_banner)
    return page


def _dash_metric(parent, col: int, label: str, value: str, *, tone: str = "muted") -> RtlLabel:
    cell = ctk.CTkFrame(
        parent, corner_radius=RADIUS_MD, fg_color=COLORS["surface_secondary"],
        border_width=1, border_color=COLORS["card_border"],
    )
    cell.grid(row=0, column=col, sticky="nsew", padx=(0, SPACE_XS) if col else 0)
    inner = ctk.CTkFrame(cell, fg_color="transparent")
    inner.pack(fill="x", padx=SPACE_SM, pady=SPACE_SM)
    head = ctk.CTkFrame(inner, fg_color="transparent")
    head.pack(fill="x")
    RtlLabel(head, label, size=9, muted=True).pack(side="right")
    color = {
        "success": COLORS["success"],
        "brand": COLORS["primary"],
        "warning": COLORS["warning"],
        "error": COLORS["error"],
        "muted": COLORS["text_primary"],
    }.get(tone, COLORS["text_primary"])
    val = RtlLabel(inner, value, size=12, bold=True)
    val.configure(text_color=color)
    val.pack(anchor="e", pady=(4, 0))
    return val
