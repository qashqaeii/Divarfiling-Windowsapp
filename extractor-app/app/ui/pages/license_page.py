"""License page — داشبورد دوستونه: لایسنس + پروفایل."""
from __future__ import annotations

import customtkinter as ctk

from app.brand import CREATOR_NAME, CREATOR_PHONE_DISPLAY
from app.ui.components.account_login_panel import build_account_login_panel
from app.ui.components.license_account_panel import build_license_account_panel
from app.ui.components import (
    AppCard,
    DangerOutlineButton,
    FieldLabel,
    OutlineButton,
    PageHero,
    PrimaryButton,
    RtlLabel,
    styled_entry,
    style_scrollable,
)
from app.ui.platform_icons import pack_icon
from app.ui.tokens import CARD_RADIUS, COLORS, SPACE_MD, SPACE_SM, SPACE_XS
from app.ui.typography import font, mono_font
from app.widgets import enable_entry_shortcuts, set_readonly_entry_value


def build_license_page(app) -> ctk.CTkFrame:
    page = ctk.CTkFrame(app._pages_container, fg_color="transparent")
    page.grid_columnconfigure(0, weight=1)
    page.grid_rowconfigure(3, weight=1)

    PageHero(
        page, "لایسنس و حساب کاربری", eyebrow="دسترسی",
        subtitle="وضعیت لایسنس، مشخصات پلن و پروفایل پلتفرم",
        icon_key="license",
    ).grid(row=0, column=0, sticky="ew", pady=(0, SPACE_SM))

    # Status banner — فشرده
    app.license_banner = ctk.CTkFrame(
        page, corner_radius=CARD_RADIUS,
        fg_color=COLORS["warning_bg"], border_width=1, border_color=COLORS["warning_border"],
    )
    app.license_banner.grid(row=1, column=0, sticky="ew", pady=(0, SPACE_SM))
    banner_row = ctk.CTkFrame(app.license_banner, fg_color="transparent")
    banner_row.pack(fill="x", padx=SPACE_MD, pady=SPACE_SM)

    app._license_status_dot = ctk.CTkFrame(
        banner_row, width=10, height=10, corner_radius=5, fg_color=COLORS["warning"],
    )
    app._license_status_dot.pack(side="right", padx=(SPACE_SM, 0), pady=4)

    status_col = ctk.CTkFrame(banner_row, fg_color="transparent")
    status_col.pack(side="right", fill="x", expand=True)
    app.license_status_lbl = RtlLabel(status_col, "در حال بررسی…", size=13, bold=True)
    app.license_status_lbl.configure(text_color=COLORS["warning"])
    app.license_status_lbl.pack(anchor="e")
    app.license_status_hint = RtlLabel(status_col, "", size=10, muted=True, wraplength=720)
    app.license_status_hint.pack(anchor="e", pady=(2, 0))

    # Actions on banner left
    banner_actions = ctk.CTkFrame(banner_row, fg_color="transparent")
    banner_actions.pack(side="left")
    OutlineButton(
        banner_actions, "تمدید / خرید", app._open_buy_license,
        icon_key="coins", width=110, height=30,
    ).pack(side="left", padx=(0, SPACE_XS))
    OutlineButton(
        banner_actions, "ورود سایت", app._open_site,
        icon_key="external_link", width=100, height=30,
    ).pack(side="left")

    # تخصiص آژانس — زیر بنر وضعیت، فقط وقتی لایسنس تخصیص‌یافته باشد
    app._license_allocation_strip = ctk.CTkFrame(
        page, corner_radius=CARD_RADIUS,
        fg_color=COLORS["info_bg"], border_width=1, border_color=COLORS["info_border"],
    )
    alloc_row = ctk.CTkFrame(app._license_allocation_strip, fg_color="transparent")
    alloc_row.pack(fill="x", padx=SPACE_MD, pady=(SPACE_SM, SPACE_SM))
    pack_icon(alloc_row, "user", size=14, side="right", padx=(SPACE_XS, 0))
    alloc_text = ctk.CTkFrame(alloc_row, fg_color="transparent")
    alloc_text.pack(side="right", fill="x", expand=True)
    app._license_allocation_lbl = RtlLabel(
        alloc_text, "", size=11, bold=True, wraplength=680,
    )
    app._license_allocation_lbl.configure(text_color=COLORS["info"])
    app._license_allocation_lbl.pack(anchor="e")
    app._license_allocation_hint = RtlLabel(
        alloc_text, "", size=10, muted=True, wraplength=680,
    )
    app._license_allocation_hint.pack(anchor="e", pady=(1, 0))

    scroll = ctk.CTkScrollableFrame(page, fg_color="transparent", corner_radius=0)
    scroll.grid(row=3, column=0, sticky="nsew")
    style_scrollable(scroll)

    body = ctk.CTkFrame(scroll, fg_color="transparent")
    body.pack(fill="both", expand=True)
    # RTL: راست = لایسنس، چپ = پروفایل — هر دو هم‌زمان
    body.grid_columnconfigure(0, weight=1, minsize=320)
    body.grid_columnconfigure(1, weight=1, minsize=340)
    body.grid_rowconfigure(0, weight=1)

    license_col = ctk.CTkFrame(body, fg_color="transparent")
    license_col.grid(row=0, column=1, sticky="nsew", padx=(SPACE_SM, 0))
    license_col.grid_columnconfigure(0, weight=1)

    profile_col = ctk.CTkFrame(body, fg_color="transparent")
    profile_col.grid(row=0, column=0, sticky="nsew", padx=(0, SPACE_SM))
    profile_col.grid_columnconfigure(0, weight=1)
    profile_col.grid_rowconfigure(0, weight=1)

    # ── ستون لایسنس (راست) ──────────────────────────────────────────
    app._account_login_card = build_account_login_panel(license_col)
    app._account_login_card.grid(row=0, column=0, sticky="ew", pady=(0, SPACE_SM))

    activate_card = AppCard(
        license_col, "کلید لایسنس",
        subtitle="فعال‌سازی یا مدیریت دسترسی",
        icon_key="sparkles", compact=True,
    )
    app._license_activate_panel = activate_card
    activate_card.grid(row=1, column=0, sticky="ew", pady=(0, SPACE_SM))
    ap = activate_card.body

    app.license_key_entry = styled_entry(
        ap, placeholder_text="کلید لایسنس را اینجا بچسبانید…",
        font=mono_font(12), height=38,
    )
    app.license_key_entry.pack(fill="x", pady=(0, SPACE_SM))
    enable_entry_shortcuts(app.license_key_entry)

    btn_row = ctk.CTkFrame(ap, fg_color="transparent")
    btn_row.pack(fill="x")
    PrimaryButton(
        btn_row, "فعال‌سازی", app._activate_license,
        icon_key="sparkles", width=110, height=34,
    ).pack(side="right")
    OutlineButton(
        btn_row, "بررسی مجدد", app._validate_license,
        icon_key="refresh", width=100, height=34,
    ).pack(side="right", padx=(SPACE_XS, 0))
    DangerOutlineButton(
        btn_row, "غیرفعال", app._deactivate_license,
        icon_key="stop", width=90, height=34,
    ).pack(side="left")

    # Plan details — همیشه در layout؛ وقتی غیرفعال empty state
    app.plan_details_card = ctk.CTkFrame(
        license_col, corner_radius=CARD_RADIUS, fg_color=COLORS["card_bg"],
        border_width=1, border_color=COLORS["card_border"],
    )
    app.plan_details_card.grid(row=2, column=0, sticky="ew", pady=(0, SPACE_SM))

    pd_head = ctk.CTkFrame(app.plan_details_card, fg_color="transparent")
    pd_head.pack(fill="x", padx=SPACE_MD, pady=(SPACE_MD, SPACE_SM))
    pack_icon(pd_head, "license", size=16, side="right", padx=(SPACE_XS, 0))
    RtlLabel(pd_head, "مشخصات پلن", size=13, bold=True).pack(side="right")

    app._plan_empty = RtlLabel(
        app.plan_details_card,
        "پس از فعال‌سازی، جزئیات پلن اینجا نمایش داده می‌شود.",
        size=11, muted=True, wraplength=360,
    )
    app._plan_empty.pack(anchor="e", padx=SPACE_MD, pady=(0, SPACE_MD))

    app._plan_body = ctk.CTkFrame(app.plan_details_card, fg_color="transparent")
    pd = app._plan_body
    pd.grid_columnconfigure((0, 1), weight=1)

    app._plan_name_lbl = _metric_cell(pd, "نام پلن", 0, 1)
    app._plan_status_lbl = _metric_cell(pd, "وضعیت", 0, 0)
    app._plan_activated_lbl = _metric_cell(pd, "فعال‌سازی", 1, 1)
    app._plan_expiry_lbl = _metric_cell(pd, "انقضا", 1, 0)
    app._plan_days_lbl = _metric_cell(pd, "روز باقی‌مانده", 2, 1)
    app._plan_devices_lbl = _metric_cell(pd, "حداکثر دستگاه", 2, 0)

    key_wrap = ctk.CTkFrame(pd, fg_color="transparent")
    key_wrap.grid(row=3, column=0, columnspan=2, sticky="ew", pady=(0, SPACE_SM))
    FieldLabel(key_wrap, "کلید لایسنس").pack(anchor="e", pady=(0, 4))
    key_box = ctk.CTkFrame(
        key_wrap, corner_radius=8, fg_color=COLORS["surface_secondary"],
        border_width=1, border_color=COLORS["card_border"],
    )
    key_box.pack(fill="x")
    app._plan_key_lbl = ctk.CTkLabel(
        key_box, text="—", font=mono_font(10),
        text_color=COLORS["text_primary"], anchor="e", justify="right", wraplength=340,
    )
    app._plan_key_lbl.pack(fill="x", padx=SPACE_SM, pady=SPACE_SM)

    # Hardware ID — فشرده
    hw_card = AppCard(license_col, "شناسه دستگاه", icon_key="user", compact=True)
    hw_card.grid(row=3, column=0, sticky="ew", pady=(0, SPACE_SM))
    hw = hw_card.body
    hw_row = ctk.CTkFrame(hw, fg_color="transparent")
    hw_row.pack(fill="x")
    OutlineButton(
        hw_row, "کپی", app._copy_hardware_id, icon_key="copy", width=64, height=30,
    ).pack(side="left")
    app.hw_id_value = app._license.get_hardware_fingerprint()
    app.hw_id_entry = styled_entry(hw_row, font=mono_font(10), height=32)
    app.hw_id_entry.pack(side="right", fill="x", expand=True, padx=(SPACE_SM, 0))
    set_readonly_entry_value(app.hw_id_entry, app.hw_id_value)
    enable_entry_shortcuts(app.hw_id_entry, readonly=True)

    # پشتیبانی فشرده
    support = ctk.CTkFrame(
        license_col, corner_radius=CARD_RADIUS, fg_color=COLORS["surface_secondary"],
        border_width=1, border_color=COLORS["card_border"],
    )
    support.grid(row=4, column=0, sticky="ew")
    sp = ctk.CTkFrame(support, fg_color="transparent")
    sp.pack(fill="x", padx=SPACE_MD, pady=SPACE_SM)
    sp_head = ctk.CTkFrame(sp, fg_color="transparent")
    sp_head.pack(fill="x")
    pack_icon(sp_head, "phone", size=14, side="right", padx=(SPACE_XS, 0))
    RtlLabel(sp_head, "پشتیبانی", size=11, bold=True).pack(side="right")
    RtlLabel(
        sp, f"{CREATOR_NAME} · {CREATOR_PHONE_DISPLAY}",
        size=10, muted=True,
    ).pack(anchor="e", pady=(SPACE_XS, SPACE_SM))
    sp_btns = ctk.CTkFrame(sp, fg_color="transparent")
    sp_btns.pack(fill="x")
    OutlineButton(
        sp_btns, "تلگرام", app._open_telegram,
        icon_key="external_link", width=80, height=28,
    ).pack(side="right")
    OutlineButton(
        sp_btns, "تماس", app._copy_creator_phone,
        icon_key="phone", width=80, height=28,
    ).pack(side="right", padx=(SPACE_XS, 0))

    # ── ستون پروفایل (چپ) — همیشه قابل مشاهده ───────────────────────
    app.license_account_card = build_license_account_panel(profile_col)
    app._license_profile_panel = app.license_account_card
    app.license_account_card.grid(row=0, column=0, sticky="nsew")

    return page


def _metric_cell(parent, label: str, row: int, col: int) -> ctk.CTkLabel:
    cell = ctk.CTkFrame(
        parent, corner_radius=8, fg_color=COLORS["surface_secondary"],
        border_width=1, border_color=COLORS["card_border"],
    )
    cell.grid(row=row, column=col, sticky="nsew", padx=(0, SPACE_XS), pady=(0, SPACE_SM))
    inner = ctk.CTkFrame(cell, fg_color="transparent")
    inner.pack(fill="x", padx=SPACE_SM, pady=SPACE_SM)
    FieldLabel(inner, label).pack(anchor="e", pady=(0, 2))
    val = ctk.CTkLabel(
        inner, text="—", font=font(12, "bold"),
        text_color=COLORS["text_primary"], anchor="e", justify="right",
    )
    val.pack(fill="x", anchor="e")
    return val
