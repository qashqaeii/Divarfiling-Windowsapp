"""Extraction page — داشبورد مرحله‌محور مینیمال."""
from __future__ import annotations

import customtkinter as ctk

from app.constants import MAX_EXTRACTION_ITEMS, TRANSACTION_TYPES
from app.formatters import fa_digits
from app.ui.components.filter_fields import AdvancedFiltersPanel
from app.ui.components import (
    AppCard,
    FieldLabel,
    OutlineButton,
    PrimaryButton,
    RtlLabel,
    SearchInput,
    styled_combobox,
    apply_combobox_rtl,
    styled_entry,
)
from app.ui.components.batch_selection import BatchSelectionPanel
from app.ui.components.fast_scroll import FastScrollableFrame
from app.ui.components.items_picker import ItemsCountPicker
from app.ui.components.mode_selector import ExtractionModeSelector
from app.ui.components.operation_workspace import OperationWorkspace
from app.ui.tokens import BUTTON_HEIGHT_CTA, CARD_RADIUS, COLORS, CONTENT_GAP, SIDEBAR_WIDTH, SPACE_MD, SPACE_SM, SPACE_XS
from app.ui.typography import font
from app.widgets import enable_entry_shortcuts, enable_textbox_shortcuts


def _sidebar_divider(parent) -> None:
    ctk.CTkFrame(parent, height=1, fg_color=COLORS["card_border"]).pack(fill="x", pady=SPACE_SM)


def _build_sidebar_location(app, parent) -> None:
    place_card = AppCard(parent, "۱. محدوده استخراج", icon_key="map_pin", compact=True, flat=True)
    place_card.pack(fill="x", pady=(0, SPACE_SM))
    pb = place_card.body

    app.place_search_entry = SearchInput(
        pb, placeholder="جستجوی سریع محله…",
        on_search=app._on_place_search,
        on_clear=lambda: app.place_search_entry.delete(0, "end"),
    )
    app.place_search_entry.pack(fill="x", pady=(0, SPACE_SM))
    enable_entry_shortcuts(app.place_search_entry.entry)
    app.place_search_entry.bind_return(app._on_place_search)

    for label, attr in (
        ("استان", "province_cb"),
        ("شهر", "city_cb"),
        ("محله (اختیاری)", "district_cb"),
    ):
        FieldLabel(pb, label).pack(anchor="e", pady=(SPACE_XS, 2))
        cb = styled_combobox(pb, state="disabled")
        cb.pack(fill="x", pady=(0, SPACE_SM))
        setattr(app, attr, cb)

    app.province_cb.configure(command=app._on_province_changed)
    app.city_cb.configure(command=app._on_city_changed)
    app.district_cb.configure(values=["—"], command=app._on_district_changed)

    app._location_status = ctk.CTkFrame(
        pb, corner_radius=8, fg_color=COLORS["success_bg"],
        border_width=1, border_color=COLORS["success_border"],
    )
    app._location_status.pack(fill="x", pady=(SPACE_XS, 0))
    status_inner = ctk.CTkFrame(app._location_status, fg_color="transparent")
    status_inner.pack(fill="x", padx=SPACE_SM, pady=SPACE_SM)
    RtlLabel(status_inner, "✓ محدوده انتخاب شد", size=11, bold=True).pack(anchor="e")
    app._location_status_detail = RtlLabel(status_inner, "—", size=10, muted=True)
    app._location_status_detail.pack(anchor="e", pady=(2, 0))
    app._location_status.pack_forget()


def _build_sidebar_mode(app, parent) -> None:
    mode_wrap = ctk.CTkFrame(parent, fg_color="transparent")
    mode_wrap.pack(fill="x", pady=(0, SPACE_SM))
    FieldLabel(mode_wrap, "۲. نوع استخراج").pack(anchor="e", pady=(0, 4))
    app._mode_selector = ExtractionModeSelector(
        mode_wrap, initial="single", on_change=app._on_extraction_mode_changed,
    )
    app._mode_selector.pack(fill="x")


def _build_sidebar_single(app, parent) -> None:
    app._single_panel = ctk.CTkFrame(parent, fg_color="transparent")
    tx_card = AppCard(app._single_panel, "دسته و زیردسته", icon_key="database", compact=True, flat=True)
    tx_card.pack(fill="x", pady=(0, SPACE_SM))
    app.transaction_type_cb = styled_combobox(
        tx_card.body, values=list(TRANSACTION_TYPES.keys()), state="readonly",
        command=app._on_transaction_changed,
    )
    app.transaction_type_cb.set("فروش مسکونی")
    app.transaction_type_cb.pack(fill="x", pady=(0, SPACE_SM))
    FieldLabel(tx_card.body, "زیردسته").pack(anchor="e", pady=(0, 4))
    app.subcategory_cb = styled_combobox(tx_card.body, state="readonly", command=app._on_subcategory_changed)
    app.subcategory_cb.pack(fill="x")
    app._set_subcategories_for_transaction("فروش مسکونی", update_preview=False)
    app._single_panel.pack(fill="x")


def _build_sidebar_batch(app, parent) -> None:
    app._batch_host = ctk.CTkFrame(parent, fg_color="transparent")
    app._batch_panel = BatchSelectionPanel(app._batch_host, app)
    app._batch_panel.pack(fill="x")
    # مخفی تا حالت گروهی انتخاب شود
    app._batch_host.pack_forget()


def _build_sidebar_output(app, parent) -> None:
    opt_card = AppCard(parent, "۳. تنظیمات خروجی", icon_key="settings", compact=True, flat=True)
    opt_card.pack(fill="x", pady=(0, SPACE_SM))
    ob = opt_card.body

    initial = int(app._settings.get("max_items", 100))
    initial = max(1, min(MAX_EXTRACTION_ITEMS, initial))
    app.items_slider = ItemsCountPicker(
        ob,
        initial=initial,
        max_items=MAX_EXTRACTION_ITEMS,
        on_change=app._on_items_changed,
        label="تعداد برای هر زیردسته",
    )
    app.items_slider.pack(fill="x", pady=(0, SPACE_SM))
    # برچسب سازگاری با کد قدیمی
    app.items_value_lbl = RtlLabel(ob, f"{fa_digits(initial)} آگهی", size=10, muted=True)
    app.items_value_lbl.pack_forget()

    FieldLabel(ob, "فرمت خروجی").pack(anchor="e", pady=(SPACE_XS, 2))
    fmt_row = ctk.CTkFrame(ob, fg_color="transparent", corner_radius=8)
    fmt_row.pack(fill="x", pady=(0, SPACE_SM))
    fmt_inner = ctk.CTkFrame(fmt_row, fg_color="transparent")
    fmt_inner.pack(fill="x", padx=3, pady=3)
    fmt_inner.grid_columnconfigure((0, 1, 2), weight=1)
    app._format_btns = {}

    def _set_format(val: str) -> None:
        app.output_format.set(val)
        _paint_format_btns()

    def _paint_format_btns() -> None:
        current = app.output_format.get()
        for val, btn in app._format_btns.items():
            if val == current:
                btn.configure(
                    fg_color=COLORS["primary"], text_color=COLORS["accent_text"],
                    hover_color=COLORS["primary_hover"],
                )
            else:
                btn.configure(
                    fg_color="transparent", text_color=COLORS["text_secondary"],
                    hover_color=COLORS["brand_soft"],
                )

    for col, (val, txt) in enumerate((("excel", "Excel"), ("csv", "CSV"), ("json", "JSON"))):
        btn = ctk.CTkButton(
            fmt_inner, text=txt, height=30, corner_radius=6, font=font(11, "bold"),
            command=lambda v=val: _set_format(v),
        )
        btn.grid(row=0, column=2 - col, sticky="ew", padx=1)
        app._format_btns[val] = btn
    _paint_format_btns()
    app.output_format.trace_add("write", lambda *_: _paint_format_btns())

    # کنار هم مطابق طرح: آپلود (راست) | دانلود (چپ)
    opts_row = ctk.CTkFrame(ob, fg_color="transparent")
    opts_row.pack(fill="x", pady=(SPACE_XS, 0))
    opts_row.grid_columnconfigure((0, 1), weight=1)

    app.download_images_cb = ctk.CTkCheckBox(
        opts_row, text="دانلود تصاویر", font=font(10),
        fg_color=COLORS["primary"], hover_color=COLORS["primary_hover"],
        checkbox_width=18, checkbox_height=18,
    )
    app.download_images_cb.grid(row=0, column=0, sticky="w", padx=(0, SPACE_XS))
    if app._settings.get("download_images"):
        app.download_images_cb.select()

    app.upload_platform_cb = ctk.CTkCheckBox(
        opts_row, text="آپلود خودکار در پلتفرم", variable=app._upload_platform_var,
        font=font(10), fg_color=COLORS["primary"], hover_color=COLORS["primary_hover"],
        checkbox_width=18, checkbox_height=18,
    )
    app.upload_platform_cb.grid(row=0, column=1, sticky="e")


def _build_sidebar_filters(app, parent) -> None:
    _sidebar_divider(parent)
    adv_card = AppCard(parent, "۴. فیلترهای پیشرفته", icon_key="filter", compact=True, flat=True)
    adv_card.pack(fill="x", pady=(0, SPACE_SM))
    ab = adv_card.body

    FieldLabel(ab, "جستجو").pack(anchor="e", pady=(0, 4))
    app.search_query_entry = styled_entry(ab, placeholder_text="مثلاً پارکینگ، معاوضه…")
    app.search_query_entry.pack(fill="x", pady=(0, SPACE_SM))
    enable_entry_shortcuts(app.search_query_entry)

    FieldLabel(ab, "نوع آگهی‌دهنده").pack(anchor="e", pady=(0, 4))
    adv_row = ctk.CTkFrame(ab, fg_color="transparent")
    adv_row.pack(fill="x", pady=(0, SPACE_SM))
    from app.filter_utils import ADVERTISER_FILTER_OPTIONS

    for idx, (val, txt) in enumerate(ADVERTISER_FILTER_OPTIONS):
        r, c = divmod(idx, 2)
        ctk.CTkRadioButton(
            adv_row, text=txt, variable=app._advertiser_filter, value=val,
            font=font(11, "bold"),
            fg_color=COLORS["primary"], hover_color=COLORS["primary_hover"],
        ).grid(row=r, column=1 - c, sticky="ew", padx=4, pady=2)
    adv_row.grid_columnconfigure((0, 1), weight=1)

    AdvancedFiltersPanel(ab, app).pack(fill="x")


def _build_sidebar(app, sidebar_col: ctk.CTkFrame) -> None:
    # عنوان سایدبار مثل طرح
    title_bar = ctk.CTkFrame(sidebar_col, fg_color="transparent")
    title_bar.grid(row=0, column=0, sticky="ew", pady=(0, SPACE_XS))
    RtlLabel(title_bar, "تنظیمات استخراج", size=13, bold=True).pack(side="right")

    sidebar = FastScrollableFrame(sidebar_col, fg_color=COLORS["app_bg"])
    sidebar.grid(row=1, column=0, sticky="nsew", padx=(0, 2))

    _build_sidebar_location(app, sidebar)
    _build_sidebar_mode(app, sidebar)
    _build_sidebar_single(app, sidebar)
    _build_sidebar_batch(app, sidebar)
    _build_sidebar_output(app, sidebar)
    _build_sidebar_filters(app, sidebar)

    action_bar = ctk.CTkFrame(sidebar_col, fg_color=COLORS["app_bg"], corner_radius=0)
    action_bar.grid(row=2, column=0, sticky="ew", pady=(SPACE_SM, SPACE_MD))
    ctk.CTkFrame(action_bar, height=1, fg_color=COLORS["card_border"]).pack(fill="x", pady=(0, SPACE_SM))

    btn_inner = ctk.CTkFrame(action_bar, fg_color="transparent")
    btn_inner.pack(fill="x", padx=SPACE_SM, pady=SPACE_SM)

    app.start_btn = PrimaryButton(btn_inner, "شروع استخراج", app._on_primary_extract, icon_key="rocket", height=BUTTON_HEIGHT_CTA)
    app.start_btn.pack(side="right", fill="x", expand=True)
    app.cancel_btn = OutlineButton(btn_inner, "لغو", app._cancel, icon_key="stop", width=72, height=BUTTON_HEIGHT_CTA)
    app.cancel_btn.pack(side="right", padx=(SPACE_SM, 0))
    app.cancel_btn.configure(state="disabled")

    app._start_hint = RtlLabel(
        action_bar,
        "دسته‌ها به‌ترتیب و بدون اجرای هم‌زمان استخراج می‌شوند.",
        size=9, muted=True,
    )
    app._start_hint.pack(anchor="e", padx=SPACE_SM, pady=(0, SPACE_SM))
    app._start_hint.pack_forget()

    for cb in (
        app.transaction_type_cb, app.subcategory_cb,
        app.province_cb, app.city_cb, app.district_cb,
    ):
        apply_combobox_rtl(cb)


def build_extraction_page(app) -> ctk.CTkFrame:
    """ساخت صفحه استخراج — workspace چپ + سایدبار ثابت راست."""
    page = ctk.CTkFrame(app._pages_container, fg_color="transparent")
    page.grid_columnconfigure(0, weight=1)
    page.grid_columnconfigure(1, weight=0, minsize=SIDEBAR_WIDTH)
    page.grid_rowconfigure(0, weight=1)

    main = ctk.CTkFrame(page, fg_color="transparent")
    main.grid(row=0, column=0, sticky="nsew", padx=(0, CONTENT_GAP))
    main.grid_rowconfigure(0, weight=1)
    main.grid_columnconfigure(0, weight=1)

    workspace = OperationWorkspace(
        main,
        on_copy_log=lambda t: _copy_log(app, t),
        on_open_folder=app._open_output_folder,
        on_open_platform=app._open_platform,
        on_retry_failed=lambda jobs: app._retry_failed_batch_jobs(jobs),
    )
    workspace.grid(row=0, column=0, sticky="nsew")
    app._workspace = workspace

    # aliases برای سازگاری با gui.py
    app._chip_province = workspace.chip_province
    app._chip_city = workspace.chip_city
    app._chip_category = workspace.chip_category
    app._chip_mode = workspace.chip_mode
    app._op_status_badge = workspace.op_status_badge
    app._summary_card_area = workspace.card_area
    app._summary_card_mode = workspace.card_mode
    app._summary_card_subs = workspace.card_subs
    app._summary_card_limit = workspace.card_limit
    app.progress = workspace.progress
    app.progress_percent = workspace.progress_percent
    app.current_task_lbl = workspace.current_task_lbl
    app.scrape_time_info = workspace.scrape_time_info
    app.stat_done = workspace.stat_done
    app.stat_total = workspace.stat_total
    app.stat_success = workspace.stat_success
    app._stat_card_total = workspace.stat_card_total
    app._stat_card_done = workspace.stat_card_done
    app._stat_card_ok = workspace.stat_card_ok
    app.log_box = workspace.log_box
    app._path_preview = workspace.path_preview
    enable_textbox_shortcuts(app.log_box, allow_edit=False)
    update_summary_chips(app)

    sidebar_col = ctk.CTkFrame(page, fg_color=COLORS["app_bg"], width=SIDEBAR_WIDTH)
    sidebar_col.grid(row=0, column=1, sticky="nsew")
    sidebar_col.grid_propagate(False)
    sidebar_col.grid_rowconfigure(1, weight=1)
    sidebar_col.grid_columnconfigure(0, weight=1)

    _build_sidebar(app, sidebar_col)

    app._update_path_preview()
    app._refresh_start_button_label()
    return page


def _copy_log(app, content: str) -> None:
    try:
        app.clipboard_clear()
        app.clipboard_append(content)
        app._set_status_message("گزارش کپی شد", tone="success")
    except Exception:
        pass


def update_summary_chips(app) -> None:
    if not hasattr(app, "_workspace"):
        return
    ws = app._workspace
    prov = app.province_cb.get() if hasattr(app, "province_cb") else ""
    city = app.city_cb.get() if hasattr(app, "city_cb") else ""
    district = app.district_cb.get() if hasattr(app, "district_cb") else ""
    parts = [p for p in (prov, city, district) if p and p != "—"]
    area = "، ".join(parts) if parts else "—"

    mode = getattr(app, "_extraction_mode", "single")
    if mode == "batch" and hasattr(app, "_batch_panel"):
        count = app._batch_panel.count_selected()
        mode_text = "استخراج گروهی"
        subs_text = f"{fa_digits(count)} زیردسته"
    else:
        mode_text = "استخراج تکی"
        cat = app.transaction_type_cb.get() if hasattr(app, "transaction_type_cb") else "—"
        sub = app.subcategory_cb.get() if hasattr(app, "subcategory_cb") else ""
        subs_text = f"{cat}" + (f" / {sub}" if sub else "")

    limit = 100
    if hasattr(app, "items_slider"):
        limit = int(round(float(app.items_slider.get())))

    ws.card_area.set_value(area)
    ws.card_mode.set_value(mode_text)
    ws.card_subs.set_value(subs_text)
    ws.card_limit.set_value(f"{fa_digits(limit)} آگهی")

    if hasattr(app, "_location_status_detail"):
        if parts:
            app._location_status_detail.configure(text=area)
            if hasattr(app, "_location_status") and not app._location_status.winfo_ismapped():
                app._location_status.pack(fill="x", pady=(SPACE_XS, 0))
        elif hasattr(app, "_location_status"):
            app._location_status.pack_forget()
