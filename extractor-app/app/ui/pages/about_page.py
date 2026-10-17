"""About page — مینیمال و یکدست."""
from __future__ import annotations

import customtkinter as ctk

from app.brand import (
    CREATOR_NAME,
    CREATOR_PHONE_DISPLAY,
    CREATOR_TELEGRAM,
    SITE_URL,
    SITE_URL_DISPLAY,
    SUPPORT_EMAIL,
)
from app.ui.components import AppCard, OutlineButton, PageHero, PrimaryButton, RtlLabel, style_scrollable
from app.ui.platform_icons import pack_icon
from app.ui.tokens import APP_VERSION, CARD_RADIUS, COLORS, SPACE_MD, SPACE_SM, SPACE_XS
from app.ui.typography import font


def build_about_page(app) -> ctk.CTkFrame:
    page = ctk.CTkFrame(app._pages_container, fg_color="transparent")
    page.grid_columnconfigure(0, weight=1)
    page.grid_rowconfigure(1, weight=1)

    PageHero(
        page, "فایلینگ دیوار", eyebrow="درباره",
        subtitle=f"نسخه {APP_VERSION} — استخراج حرفه‌ای برای مشاوران",
        logo_image=app._brand_logo_image(24),
    ).grid(row=0, column=0, sticky="ew", pady=(0, SPACE_SM))

    scroll = ctk.CTkScrollableFrame(page, fg_color="transparent", corner_radius=0)
    scroll.grid(row=1, column=0, sticky="nsew")
    style_scrollable(scroll)

    cards = ctk.CTkFrame(scroll, fg_color="transparent")
    cards.pack(fill="both", expand=True)
    cards.grid_columnconfigure((0, 1, 2), weight=1)

    _about_card(cards, 2, "وب‌سایت", SITE_URL_DISPLAY, SITE_URL, icon_key="external_link", btns=[
        ("باز کردن سایت", app._open_site, True, "external_link"),
        ("خرید لایسنس", app._open_buy_license, False, "coins"),
    ])
    _about_card(cards, 1, "پشتیبانی", SUPPORT_EMAIL, "فعال‌سازی و خطای فنی", icon_key="help_center", btns=[
        (CREATOR_PHONE_DISPLAY, app._copy_creator_phone, False, "phone"),
    ])
    _about_card(cards, 0, "سازنده", CREATOR_NAME, "طراحی و توسعه محصول", icon_key="user", btns=[
        (CREATOR_TELEGRAM, app._open_telegram, False, "external_link"),
    ])

    # Feature highlights
    highlights = ctk.CTkFrame(
        cards, corner_radius=CARD_RADIUS, fg_color=COLORS["surface_secondary"],
        border_width=1, border_color=COLORS["card_border"],
    )
    highlights.grid(row=1, column=0, columnspan=3, sticky="ew", pady=(SPACE_MD, 0))
    hi = ctk.CTkFrame(highlights, fg_color="transparent")
    hi.pack(fill="x", padx=SPACE_MD, pady=SPACE_MD)
    hi.grid_columnconfigure((0, 1, 2), weight=1)
    for col, (icon, title, desc) in enumerate((
        ("extract", "استخراج سریع", "آگهی‌های دیوار با فیلتر پیشرفته"),
        ("upload", "آپلود خودکار", "انتقال مستقیم به پلتفرم"),
        ("automation", "زمان‌بندی", "استخراج دوره‌ای بدون نظارت"),
    )):
        cell = ctk.CTkFrame(hi, fg_color="transparent")
        cell.grid(row=0, column=2 - col, sticky="nsew", padx=SPACE_SM)
        head = ctk.CTkFrame(cell, fg_color="transparent")
        head.pack(fill="x")
        pack_icon(head, icon, size=16, side="right", padx=(SPACE_XS, 0))
        RtlLabel(head, title, size=12, bold=True).pack(side="right")
        RtlLabel(cell, desc, size=10, muted=True, wraplength=200).pack(anchor="e", pady=(4, 0))

    footer = ctk.CTkFrame(
        page, corner_radius=CARD_RADIUS, fg_color=COLORS["card_bg"],
        border_width=1, border_color=COLORS["card_border"],
    )
    footer.grid(row=2, column=0, sticky="ew", pady=(SPACE_SM, 0))
    fb = ctk.CTkFrame(footer, fg_color="transparent")
    fb.pack(fill="x", padx=SPACE_MD, pady=SPACE_MD)
    RtlLabel(
        fb,
        "ابزار تخصصی استخراج آگهی‌های دیوار برای مشاوران املاک — سریع، دقیق و قابل اعتماد.",
        size=11, muted=True, wraplength=700,
    ).pack(anchor="e", pady=(0, SPACE_SM))
    row = ctk.CTkFrame(fb, fg_color="transparent")
    row.pack(fill="x")
    RtlLabel(row, f"© divarfiling.ir · Build {APP_VERSION}", size=10, muted=True).pack(side="right")
    OutlineButton(row, "بررسی بروزرسانی", app._open_site, icon_key="refresh", width=140, height=30).pack(side="left")

    return page


def _about_card(
    parent, col: int, title: str, value: str, subtitle: str,
    *, icon_key: str = "",
    btns: list[tuple[str, object, bool, str]],
) -> None:
    card = AppCard(parent, title, subtitle=subtitle, icon_key=icon_key, compact=True)
    card.grid(row=0, column=col, sticky="nsew", padx=(0 if col == 2 else SPACE_SM, SPACE_SM if col == 0 else 0))
    body = card.body

    RtlLabel(body, value, size=15, bold=True).pack(anchor="e", pady=(0, SPACE_SM))
    btn_row = ctk.CTkFrame(body, fg_color="transparent")
    btn_row.pack(fill="x")
    for text, cmd, primary, btn_icon in btns:
        if primary:
            PrimaryButton(btn_row, text, cmd, icon_key=btn_icon, width=130, height=30).pack(
                side="right", padx=(SPACE_SM, 0),
            )
        else:
            OutlineButton(btn_row, text, cmd, icon_key=btn_icon, width=130, height=30, font=font(10)).pack(
                side="right", padx=(SPACE_SM, 0),
            )
