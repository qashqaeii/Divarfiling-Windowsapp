"""پنل پروفایل کاربر و املاک — صفحه لایسنس (همیشه قابل مشاهده)."""
from __future__ import annotations

from typing import Any, Dict, List, Optional

import customtkinter as ctk

from app.formatters import fa_digits, format_price_toman
from app.ui.components import ChipBadge, FieldLabel, RtlLabel
from app.ui.platform_icons import pack_icon
from app.ui.tokens import CARD_RADIUS, COLORS, SPACE_MD, SPACE_SM, SPACE_XS
from app.ui.typography import font


_ROLE_LABELS = {
    "owner": "مالک آژانس",
    "manager": "مدیر",
    "advisor": "مشاور",
    "secretary": "منشی",
}


def build_license_account_panel(parent) -> ctk.CTkFrame:
    """ساخت پنل پروفایل — همیشه نمایش داده می‌شود (با empty state)."""
    card = ctk.CTkFrame(
        parent, corner_radius=CARD_RADIUS, fg_color=COLORS["card_bg"],
        border_width=1, border_color=COLORS["card_border"],
    )

    head = ctk.CTkFrame(card, fg_color="transparent")
    head.pack(fill="x", padx=SPACE_MD, pady=(SPACE_MD, SPACE_SM))
    pack_icon(head, "user", size=18, side="right", padx=(SPACE_SM, 0))
    RtlLabel(head, "پروفایل پلتفرم", size=14, bold=True).pack(side="right")
    subtitle = RtlLabel(head, "در انتظار همگام‌سازی", size=10, muted=True)
    subtitle.pack(side="left")

    # Empty state (قبل از فعال‌سازی / بدون پروفایل)
    empty_wrap = ctk.CTkFrame(card, fg_color="transparent")
    empty_lbl = RtlLabel(
        empty_wrap,
        "پس از فعال‌سازی لایسنس، اطلاعات حساب و املاک پلتفرم اینجا نمایش داده می‌شود.",
        size=11, muted=True, wraplength=360,
    )
    empty_lbl.pack(anchor="e", padx=SPACE_MD, pady=(SPACE_SM, SPACE_MD))
    empty_wrap.pack(fill="x")

    # Content (مخفی تا داده بیاید)
    content = ctk.CTkFrame(card, fg_color="transparent")

    profile_grid = ctk.CTkFrame(content, fg_color="transparent")
    profile_grid.pack(fill="x", padx=SPACE_MD, pady=(0, SPACE_SM))
    profile_grid.grid_columnconfigure((0, 1), weight=1)

    profile_cells: Dict[str, ctk.CTkLabel] = {}
    fields = (
        ("display_name", "نام"),
        ("phone", "موبایل"),
        ("agency_name", "آژانس / دفتر"),
        ("city", "شهر"),
        ("email", "ایمیل"),
        ("role", "نقش"),
    )
    for idx, (key, label) in enumerate(fields):
        row, col = divmod(idx, 2)
        col = 1 - col
        cell = _info_cell(profile_grid, label, row, col)
        profile_cells[key] = cell

    chips_row = ctk.CTkFrame(content, fg_color="transparent")
    chips_row.pack(fill="x", padx=SPACE_MD, pady=(0, SPACE_SM))
    stat_chips: Dict[str, ChipBadge] = {}
    for key, label, icon in (
        ("total", "کل املاک", "database"),
        ("sale", "فروش", "coins"),
        ("rent", "اجاره", "building"),
        ("active", "فعال", "sparkles"),
    ):
        chip = ChipBadge(chips_row, f"{label}: —", icon_key=icon)
        chip.pack(side="right", padx=(SPACE_XS, 0))
        stat_chips[key] = chip

    props_head = ctk.CTkFrame(content, fg_color="transparent")
    props_head.pack(fill="x", padx=SPACE_MD, pady=(SPACE_XS, SPACE_XS))
    pack_icon(props_head, "building", size=16, side="right", padx=(SPACE_XS, 0))
    RtlLabel(props_head, "املاک ثبت‌شده", size=12, bold=True).pack(side="right")

    props_wrap = ctk.CTkFrame(content, fg_color="transparent")
    props_wrap.pack(fill="both", expand=True, padx=SPACE_MD, pady=(0, SPACE_MD))
    props_wrap.grid_rowconfigure(0, weight=1)
    props_wrap.grid_columnconfigure(0, weight=1)

    props_scroll = ctk.CTkScrollableFrame(
        props_wrap, fg_color=COLORS["surface_secondary"], height=200,
    )
    props_scroll.grid(row=0, column=0, sticky="nsew")

    props_empty = RtlLabel(
        props_scroll,
        "هنوز ملکی در پلتفرم ثبت نشده.",
        size=11, muted=True, wraplength=320,
    )
    props_empty.pack(anchor="e", padx=SPACE_SM, pady=SPACE_SM)

    card._license_account_refs = {
        "card": card,
        "subtitle": subtitle,
        "empty_wrap": empty_wrap,
        "content": content,
        "profile_cells": profile_cells,
        "stat_chips": stat_chips,
        "props_scroll": props_scroll,
        "empty_lbl": props_empty,
        "property_rows": [],
    }
    return card


def update_license_account_panel(card: ctk.CTkFrame, account: Optional[Dict[str, Any]]) -> None:
    """به‌روزرسانی پنل — همیشه visible؛ بدون داده = empty state."""
    refs = getattr(card, "_license_account_refs", None)
    if not refs:
        return

    # همیشه نشان بده
    try:
        card.grid()
    except Exception:
        pass

    has_profile = bool(account and isinstance(account, dict))
    display_name = ""
    if has_profile:
        display_name = str(account.get("display_name") or "").strip()
        if not display_name and not account.get("phone"):
            has_profile = False

    if not has_profile:
        refs["subtitle"].configure(text="در انتظار همگام‌سازی")
        refs["content"].pack_forget()
        if not refs["empty_wrap"].winfo_ismapped():
            refs["empty_wrap"].pack(fill="x")
        return

    refs["empty_wrap"].pack_forget()
    if not refs["content"].winfo_ismapped():
        refs["content"].pack(fill="both", expand=True)

    stats = account.get("stats") or {}
    props: List[Dict[str, Any]] = list(account.get("properties") or [])

    refs["subtitle"].configure(
        text="همگام با حساب پلتفرم" if account.get("has_profile") else "پروفایل ناقص — از سایت تکمیل کنید",
    )

    values = {
        "display_name": display_name or "—",
        "phone": fa_digits(account.get("phone") or "—"),
        "agency_name": account.get("agency_name") or "—",
        "city": account.get("city") or account.get("agency_city") or "—",
        "email": account.get("email") or "—",
        "role": _ROLE_LABELS.get(str(account.get("role") or ""), account.get("role") or "—"),
    }
    for key, lbl in refs["profile_cells"].items():
        lbl.configure(text=values.get(key, "—"))

    chip_texts = {
        "total": f"کل املاک: {fa_digits(stats.get('total', 0))}",
        "sale": f"فروش: {fa_digits(stats.get('sale', 0))}",
        "rent": f"اجاره: {fa_digits(stats.get('rent', 0))}",
        "active": f"فعال: {fa_digits(stats.get('active', 0))}",
    }
    for key, chip in refs["stat_chips"].items():
        chip.set_text(chip_texts.get(key, "—"))

    scroll: ctk.CTkScrollableFrame = refs["props_scroll"]
    for row in refs["property_rows"]:
        try:
            row.destroy()
        except Exception:
            pass
    refs["property_rows"] = []

    refs["empty_lbl"].pack_forget()
    if not props:
        refs["empty_lbl"].configure(
            text="هنوز ملکی در پلتفرم ثبت نشده — از داشبورد وب املاک خود را اضافه کنید.",
        )
        refs["empty_lbl"].pack(anchor="e", padx=SPACE_SM, pady=SPACE_SM)
    else:
        for prop in props:
            refs["property_rows"].append(_property_row(scroll, prop))
        if account.get("properties_truncated"):
            more = RtlLabel(
                scroll,
                f"و {fa_digits((stats.get('total') or 0) - len(props))} ملک دیگر در پلتفرم…",
                size=10, muted=True,
            )
            more.pack(anchor="e", padx=SPACE_SM, pady=(0, SPACE_SM))
            refs["property_rows"].append(more)


def _info_cell(parent, label: str, row: int, col: int) -> ctk.CTkLabel:
    cell = ctk.CTkFrame(
        parent, corner_radius=8, fg_color=COLORS["surface_secondary"],
        border_width=1, border_color=COLORS["card_border"],
    )
    cell.grid(row=row, column=col, sticky="nsew", padx=(0, SPACE_XS), pady=(0, SPACE_SM))
    inner = ctk.CTkFrame(cell, fg_color="transparent")
    inner.pack(fill="x", padx=SPACE_SM, pady=SPACE_SM)
    FieldLabel(inner, label).pack(anchor="e", pady=(0, 4))
    val = ctk.CTkLabel(
        inner, text="—", font=font(12, "bold"),
        text_color=COLORS["text_primary"], anchor="e", justify="right",
    )
    val.pack(fill="x", anchor="e")
    return val


def _property_row(parent, prop: Dict[str, Any]) -> ctk.CTkFrame:
    row = ctk.CTkFrame(
        parent, corner_radius=8, fg_color=COLORS["card_bg"],
        border_width=1, border_color=COLORS["card_border"],
    )
    row.pack(fill="x", padx=SPACE_XS, pady=(0, SPACE_XS))

    top = ctk.CTkFrame(row, fg_color="transparent")
    top.pack(fill="x", padx=SPACE_SM, pady=(SPACE_SM, 2))
    RtlLabel(
        top, str(prop.get("title") or "—"), size=12, bold=True, wraplength=320,
    ).pack(side="right", fill="x", expand=True)

    meta = ctk.CTkFrame(row, fg_color="transparent")
    meta.pack(fill="x", padx=SPACE_SM, pady=(0, SPACE_XS))
    deal = prop.get("deal_mode") or "—"
    ptype = prop.get("property_type") or ""
    RtlLabel(meta, f"{deal} · {ptype}".strip(" · "), size=10, muted=True).pack(side="right")

    details = ctk.CTkFrame(row, fg_color="transparent")
    details.pack(fill="x", padx=SPACE_SM, pady=(0, SPACE_SM))

    loc = prop.get("location") or "—"
    area = prop.get("area")
    rooms = prop.get("rooms") or ""
    specs = []
    if loc and loc != "—":
        specs.append(loc)
    if area:
        specs.append(f"{fa_digits(int(area))} متر")
    if rooms:
        specs.append(f"{fa_digits(rooms)} اتاق")
    RtlLabel(details, " · ".join(specs) if specs else "—", size=10).pack(side="right")

    price_txt = _property_price_text(prop)
    if price_txt:
        RtlLabel(details, price_txt, size=10, bold=True).pack(side="left")

    amenities = prop.get("amenities") or []
    if amenities:
        amen_row = ctk.CTkFrame(row, fg_color="transparent")
        amen_row.pack(fill="x", padx=SPACE_SM, pady=(0, SPACE_SM))
        for name in amenities[:4]:
            ChipBadge(amen_row, name).pack(side="right", padx=(SPACE_XS, 0))

    return row


def _property_price_text(prop: Dict[str, Any]) -> str:
    if prop.get("monthly_rent") or prop.get("deposit"):
        parts = []
        if prop.get("deposit"):
            parts.append(f"رهن {format_price_toman(prop.get('deposit'))}")
        if prop.get("monthly_rent"):
            parts.append(f"اجاره {format_price_toman(prop.get('monthly_rent'))}")
        return " · ".join(parts)
    if prop.get("sale_price"):
        return format_price_toman(prop.get("sale_price"))
    return ""
