"""Settings page — مینیمال با اسکرول پایدار."""
from __future__ import annotations

import customtkinter as ctk

from app.brand import DEFAULT_LICENSE_API_URL, DEFAULT_PLATFORM_UPLOAD_URL
from app.formatters import fa_digits
from app.notifications import default_notification_settings, is_windows_notifications_supported
from app.system_tray import is_system_tray_supported
from app.tray_settings import default_tray_settings
from app.ui.components import (
    DangerOutlineButton,
    FieldLabel,
    OutlineButton,
    PageHero,
    PrimaryButton,
    RtlLabel,
    style_scrollable,
)
from app.ui.tokens import CARD_RADIUS, COLORS, INPUT_RADIUS, SPACE_MD, SPACE_SM, SPACE_XS
from app.ui.typography import font, mono_font
from app.ui.platform_icons import pack_icon


def build_settings_page(app) -> ctk.CTkFrame:
    page = ctk.CTkFrame(app._pages_container, fg_color="transparent")
    page.grid_columnconfigure(0, weight=1)
    page.grid_rowconfigure(1, weight=1)

    PageHero(
        page, "پیکربندی عمومی", eyebrow="تنظیمات",
        subtitle="عملکرد، ظاهر و اتصال", icon_key="settings",
    ).grid(row=0, column=0, sticky="ew", pady=(0, SPACE_SM))

    saved_workers = int(app._settings.get("max_workers", 6))
    saved_appearance = app._settings.get("appearance", "light")
    notify_cfg = default_notification_settings()
    notify_cfg.update(app._settings.get("notifications") or {})
    tray_cfg = default_tray_settings()
    tray_cfg.update(app._settings.get("tray") or {})
    raw_tray = app._settings.get("tray") or {}
    if "notify_extraction_complete" not in raw_tray:
        tray_cfg["notify_extraction_complete"] = bool(notify_cfg.get("extraction", True))
    if "notify_errors" not in raw_tray:
        tray_cfg["notify_errors"] = bool(notify_cfg.get("errors", True))

    scroll = ctk.CTkScrollableFrame(page, fg_color="transparent", corner_radius=0)
    scroll.grid(row=1, column=0, sticky="nsew")
    style_scrollable(scroll)

    body = ctk.CTkFrame(scroll, fg_color="transparent")
    body.pack(fill="both", expand=True)
    body.grid_columnconfigure((0, 1), weight=1)

    # Performance
    perf_panel, perf_body = _section(body, "عملکرد", "تعداد worker موازی", icon_key="zap")
    perf_panel.grid(row=0, column=0, sticky="nsew", padx=(0, SPACE_SM), pady=(0, SPACE_SM))

    worker_head = ctk.CTkFrame(perf_body, fg_color="transparent")
    worker_head.pack(fill="x", pady=(0, SPACE_XS))
    FieldLabel(worker_head, "تعداد Worker").pack(side="right")
    app.workers_lbl = RtlLabel(worker_head, fa_digits(saved_workers), size=20, bold=True)
    app.workers_lbl.configure(text_color=COLORS["primary"])
    app.workers_lbl.pack(side="right", padx=(SPACE_SM, 0))

    app.workers_slider = ctk.CTkSlider(
        perf_body, from_=1, to=12, number_of_steps=11,
        command=app._on_workers_changed,
        progress_color=COLORS["primary"], button_color=COLORS["primary_end"],
        button_hover_color=COLORS["primary_hover"],
    )
    app.workers_slider.set(float(saved_workers))
    app.workers_slider.pack(fill="x", pady=(0, SPACE_XS))
    scale = ctk.CTkFrame(perf_body, fg_color="transparent")
    scale.pack(fill="x", pady=(0, SPACE_SM))
    RtlLabel(scale, "۱", size=9, muted=True).pack(side="right")
    RtlLabel(scale, "۱۲", size=9, muted=True).pack(side="left")
    RtlLabel(
        perf_body,
        "مقدار پیشنهادی: ۶ — بیشتر = سریع‌تر ولی مصرف بیشتر CPU/RAM",
        size=10, muted=True, wraplength=340,
    ).pack(anchor="e")

    # Appearance — theme cards
    appear_panel, appear_body = _section(body, "ظاهر", "تم رابط کاربری", icon_key="theme")
    appear_panel.grid(row=0, column=1, sticky="nsew", padx=(SPACE_SM, 0), pady=(0, SPACE_SM))

    app._appearance_var = ctk.StringVar(value=saved_appearance)
    theme_row = ctk.CTkFrame(appear_body, fg_color="transparent")
    theme_row.pack(fill="x")
    theme_row.grid_columnconfigure((0, 1, 2), weight=1)

    themes = (
        ("light", "روشن", COLORS["surface"][0]),
        ("dark", "تاریک", "#1E293B"),
        ("system", "سیستم", COLORS["surface_secondary"][0]),
    )
    for col, (val, txt, preview_color) in enumerate(themes):
        card = ctk.CTkFrame(
            theme_row, corner_radius=10, fg_color=COLORS["surface_secondary"],
            border_width=2, border_color=COLORS["card_border"],
        )
        card.grid(row=0, column=2 - col, sticky="nsew", padx=3)
        preview = ctk.CTkFrame(card, height=28, corner_radius=6, fg_color=preview_color)
        preview.pack(fill="x", padx=SPACE_SM, pady=(SPACE_SM, SPACE_XS))
        preview.pack_propagate(False)
        ctk.CTkRadioButton(
            card, text=txt, variable=app._appearance_var, value=val,
            command=lambda v=val: app._on_appearance_changed(v),
            font=font(11, "bold"), fg_color=COLORS["primary"],
        ).pack(anchor="e", padx=SPACE_SM, pady=(0, SPACE_SM))

    # Notifications (Windows)
    notify_panel, notify_body = _section(
        body, "اعلان‌های ویندوز", "Toast بومی با لوگو اپ", icon_key="bell",
    )
    app._notify_panel = notify_panel
    notify_panel.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(0, SPACE_SM))

    support_txt = (
        "اعلان‌های بومی ویندوز ۱۰/۱۱ با آیکن برند — از Action Center ویندوز نمایش داده می‌شوند."
        if is_windows_notifications_supported()
        else "اعلان بومی فقط در ویندوز پشتیبانی می‌شود."
    )
    RtlLabel(notify_body, support_txt, size=10, muted=True, wraplength=720).pack(
        anchor="e", pady=(0, SPACE_SM),
    )

    notify_grid = ctk.CTkFrame(notify_body, fg_color="transparent")
    notify_grid.pack(fill="x")
    notify_grid.grid_columnconfigure((0, 1, 2, 3), weight=1)

    app._notify_enabled_var = ctk.BooleanVar(value=bool(notify_cfg.get("enabled", True)))
    app._notify_sound_var = ctk.BooleanVar(value=bool(notify_cfg.get("sound", True)))
    app._notify_minimized_var = ctk.BooleanVar(value=bool(notify_cfg.get("when_minimized_only", False)))
    app._notify_extraction_var = ctk.BooleanVar(value=bool(notify_cfg.get("extraction", True)))
    app._notify_scheduler_var = ctk.BooleanVar(value=bool(notify_cfg.get("scheduler", True)))
    app._notify_license_var = ctk.BooleanVar(value=bool(notify_cfg.get("license", True)))
    app._notify_errors_var = ctk.BooleanVar(value=bool(notify_cfg.get("errors", True)))
    app._notify_upload_var = ctk.BooleanVar(value=bool(notify_cfg.get("upload", True)))

    notify_checks = (
        (app._notify_enabled_var, "فعال‌سازی اعلان‌ها"),
        (app._notify_sound_var, "صدای اعلان"),
        (app._notify_minimized_var, "فقط وقتی پنجره کوچک شده"),
        (app._notify_extraction_var, "استخراج"),
        (app._notify_scheduler_var, "زمان‌بندی"),
        (app._notify_license_var, "لایسنس"),
        (app._notify_errors_var, "خطاها"),
        (app._notify_upload_var, "آپلود پلتفرم"),
    )
    for idx, (var, label) in enumerate(notify_checks):
        row, col = divmod(idx, 4)
        ctk.CTkCheckBox(
            notify_grid, text=label, variable=var, font=font(11),
            fg_color=COLORS["primary"], hover_color=COLORS["primary_hover"],
        ).grid(row=row, column=3 - col, sticky="ew", padx=4, pady=4)

    notify_actions = ctk.CTkFrame(notify_body, fg_color="transparent")
    notify_actions.pack(fill="x", pady=(SPACE_SM, 0))
    OutlineButton(
        notify_actions, "ارسال تست", app._test_windows_notification,
        icon_key="bell", height=32, width=120,
    ).pack(side="right")

    # System Tray / Background
    tray_panel, tray_body = _section(
        body, "پس‌زمینه و System Tray", "اجرای بدون وقفه با آیکن کنار ساعت ویندوز",
        icon_key="automation",
    )
    app._tray_panel = tray_panel
    tray_panel.grid(row=2, column=0, columnspan=2, sticky="ew", pady=(0, SPACE_SM))

    tray_support = (
        "با بستن پنجره (×)، برنامه مخفی می‌شود و استخراج/زمان‌بندی در پس‌زمینه ادامه می‌یابد."
        if is_system_tray_supported()
        else "System Tray روی این سیستم در دسترس نیست — بستن پنجره برنامه را کامل می‌بندد."
    )
    RtlLabel(tray_body, tray_support, size=10, muted=True, wraplength=720).pack(
        anchor="e", pady=(0, SPACE_SM),
    )

    app._tray_close_to_tray_var = ctk.BooleanVar(value=bool(tray_cfg.get("close_to_tray", True)))
    # هم‌تراز با چک‌باکس‌های اعلان (همان BooleanVar)
    app._tray_notify_extraction_var = app._notify_extraction_var
    app._tray_notify_errors_var = app._notify_errors_var
    # مقدار اولیه از tray_cfg اگر متفاوت بود
    app._notify_extraction_var.set(bool(tray_cfg.get("notify_extraction_complete", True)))
    app._notify_errors_var.set(bool(tray_cfg.get("notify_errors", True)))

    tray_grid = ctk.CTkFrame(tray_body, fg_color="transparent")
    tray_grid.pack(fill="x")
    tray_grid.grid_columnconfigure((0, 1, 2), weight=1)

    tray_checks = (
        (app._tray_close_to_tray_var, "با بستن پنجره، برنامه در پس‌زمینه فعال بماند"),
        (app._tray_notify_extraction_var, "نمایش اعلان پایان استخراج"),
        (app._tray_notify_errors_var, "نمایش اعلان خطاها"),
    )
    for col, (var, label) in enumerate(tray_checks):
        ctk.CTkCheckBox(
            tray_grid, text=label, variable=var, font=font(11),
            fg_color=COLORS["primary"], hover_color=COLORS["primary_hover"],
        ).grid(row=0, column=2 - col, sticky="ew", padx=4, pady=4)

    tray_actions = ctk.CTkFrame(tray_body, fg_color="transparent")
    tray_actions.pack(fill="x", pady=(SPACE_SM, 0))
    DangerOutlineButton(
        tray_actions, "خروج کامل از برنامه", app._quit_application,
        icon_key="stop", height=32, width=180,
    ).pack(side="right")

    # Connection
    conn_panel, conn_body = _section(body, "اتصال و API", "آدرس‌های ثابت سرور", icon_key="api")
    app._settings_conn_panel = conn_panel
    conn_panel.grid(row=3, column=0, columnspan=2, sticky="ew", pady=(0, SPACE_SM))

    conn_grid = ctk.CTkFrame(conn_body, fg_color="transparent")
    conn_grid.pack(fill="x")
    conn_grid.grid_columnconfigure((0, 1), weight=1)

    _url_field(conn_grid, "آدرس API لایسنس", DEFAULT_LICENSE_API_URL.rstrip("/"), row=0, col=1)
    _url_field(conn_grid, "آدرس آپلود پلتفرم", DEFAULT_PLATFORM_UPLOAD_URL.rstrip("/"), row=0, col=0)
    RtlLabel(
        conn_body, "آدرس‌ها ثابت هستند — برای امنیت قابل تغییر نیستند.",
        size=10, muted=True,
    ).pack(anchor="e", pady=(SPACE_SM, 0))

    # Footer — ثابت خارج از اسکرول
    footer = ctk.CTkFrame(
        page, corner_radius=CARD_RADIUS, fg_color=COLORS["card_bg"],
        border_width=1, border_color=COLORS["card_border"],
    )
    footer.grid(row=2, column=0, sticky="ew", pady=(SPACE_SM, 0))
    footer_inner = ctk.CTkFrame(footer, fg_color="transparent")
    footer_inner.pack(fill="x", padx=SPACE_MD, pady=SPACE_SM)
    btn_row = ctk.CTkFrame(footer_inner, fg_color="transparent")
    btn_row.pack(side="right")
    PrimaryButton(
        btn_row, "ذخیره تنظیمات", app._save_settings,
        icon_key="save", height=38, width=150,
    ).pack(side="right")
    OutlineButton(
        btn_row, "بازنشانی", app._reset_settings_defaults,
        icon_key="refresh", height=38, width=118,
    ).pack(side="right", padx=(SPACE_SM, 0))
    RtlLabel(
        footer_inner, "تغییرات ذخیره‌نشده پس از بستن از بین می‌روند",
        size=9, muted=True,
    ).pack(side="right", padx=(0, SPACE_MD))

    app._on_workers_changed(app.workers_slider.get())
    return page


def _section(master, title: str, subtitle: str, *, icon_key: str = "") -> tuple[ctk.CTkFrame, ctk.CTkFrame]:
    panel = ctk.CTkFrame(
        master, corner_radius=CARD_RADIUS, fg_color=COLORS["card_bg"],
        border_width=1, border_color=COLORS["card_border"],
    )
    body = ctk.CTkFrame(panel, fg_color="transparent")
    body.pack(fill="both", expand=True, padx=SPACE_MD, pady=SPACE_MD)
    head = ctk.CTkFrame(body, fg_color="transparent")
    head.pack(fill="x", pady=(0, 4))
    if icon_key:
        pack_icon(head, icon_key, size=20, side="right", padx=(SPACE_SM, 0))
    RtlLabel(head, title, size=14, bold=True).pack(side="right")
    RtlLabel(body, subtitle, size=10, muted=True).pack(anchor="e", pady=(0, SPACE_SM))
    return panel, body


def _url_field(parent, label: str, url: str, *, row: int, col: int) -> None:
    wrap = ctk.CTkFrame(parent, fg_color="transparent")
    wrap.grid(row=row, column=col, sticky="nsew", padx=4, pady=4)
    FieldLabel(wrap, label).pack(anchor="e", pady=(0, SPACE_XS))
    row_f = ctk.CTkFrame(
        wrap, fg_color=COLORS["surface_secondary"], corner_radius=INPUT_RADIUS,
        border_width=1, border_color=COLORS["input_border"],
    )
    row_f.pack(fill="x")
    ctk.CTkLabel(
        row_f, text=url, font=mono_font(10), text_color=COLORS["text_secondary"],
        anchor="w", justify="left",
    ).pack(fill="x", padx=SPACE_MD, pady=10)
