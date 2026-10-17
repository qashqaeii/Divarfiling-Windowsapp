"""Output page — داشبورد خروجی مینیمال."""
from __future__ import annotations

import customtkinter as ctk

from app.paths import get_output_dir
from app.ui.components import (
    AppCard,
    EmptyState,
    OutlineButton,
    PageHero,
    PathField,
    PrimaryButton,
    RtlLabel,
    StatCard,
    style_scrollable,
)
from app.ui.platform_icons import pack_icon
from app.ui.tokens import CARD_RADIUS, COLORS, SPACE_MD, SPACE_SM, SPACE_XS
from app.ui.typography import mono_font


def build_output_page(app) -> ctk.CTkFrame:
    page = ctk.CTkFrame(app._pages_container, fg_color="transparent")
    page.grid_columnconfigure(0, weight=1)
    page.grid_rowconfigure(1, weight=1)

    PageHero(
        page, "خروجی‌ها", eyebrow="خروجی",
        subtitle="فایل‌های استخراج‌شده و مسیر ذخیره‌سازی", icon_key="output",
    ).grid(row=0, column=0, sticky="ew", pady=(0, SPACE_SM))

    scroll = ctk.CTkScrollableFrame(page, fg_color="transparent", corner_radius=0)
    scroll.grid(row=1, column=0, sticky="nsew")
    style_scrollable(scroll)

    content = ctk.CTkFrame(scroll, fg_color="transparent")
    content.pack(fill="both", expand=True)
    content.grid_columnconfigure(0, weight=1)

    # Quick actions strip
    actions = ctk.CTkFrame(
        content, corner_radius=CARD_RADIUS, fg_color=COLORS["surface_secondary"],
        border_width=1, border_color=COLORS["card_border"],
    )
    actions.pack(fill="x", pady=(0, SPACE_MD))
    ai = ctk.CTkFrame(actions, fg_color="transparent")
    ai.pack(fill="x", padx=SPACE_MD, pady=SPACE_SM)
    RtlLabel(ai, "دسترسی سریع", size=11, muted=True).pack(side="right", padx=(SPACE_SM, 0))
    pack_icon(ai, "folder", size=16, side="right")
    btn_strip = ctk.CTkFrame(ai, fg_color="transparent")
    btn_strip.pack(side="left")
    PrimaryButton(
        btn_strip, "باز کردن پوشه", app._open_output_folder,
        icon_key="folder", width=140, height=34,
    ).pack(side="left", padx=(0, SPACE_XS))
    OutlineButton(
        btn_strip, "کپی مسیر", app._copy_output_dir, icon_key="copy", width=100, height=34,
    ).pack(side="left", padx=(0, SPACE_XS))
    OutlineButton(
        btn_strip, "آپلود پلتفرم", app._open_platform, icon_key="upload", width=120, height=34,
    ).pack(side="left")

    # Latest output card
    latest_card = AppCard(content, "آخرین خروجی", subtitle="آمار فایل تولیدشده", icon_key="file_text")
    latest_card.pack(fill="x", pady=(0, SPACE_MD))
    lb = latest_card.body

    grid = ctk.CTkFrame(lb, fg_color="transparent")
    grid.pack(fill="x")
    grid.grid_columnconfigure((0, 1, 2, 3), weight=1)
    app._out_stat_file = StatCard(grid, "نام فایل", "—", icon_key="file_text")
    app._out_stat_file.grid(row=0, column=3, sticky="ew", padx=(SPACE_XS, 0))
    app._out_stat_records = StatCard(grid, "رکورد", "—", icon_key="database")
    app._out_stat_records.grid(row=0, column=2, sticky="ew", padx=SPACE_XS)
    app._out_stat_time = StatCard(grid, "زمان", "—", icon_key="calendar")
    app._out_stat_time.grid(row=0, column=1, sticky="ew", padx=SPACE_XS)
    app._out_stat_size = StatCard(grid, "حجم", "—", icon_key="bar_chart")
    app._out_stat_size.grid(row=0, column=0, sticky="ew", padx=(0, SPACE_XS))

    latest_actions = ctk.CTkFrame(lb, fg_color="transparent")
    latest_actions.pack(fill="x", pady=(SPACE_MD, 0))
    PrimaryButton(
        latest_actions, "آپلود پلتفرم", app._open_platform,
        icon_key="upload", width=130, height=34,
    ).pack(side="right")
    OutlineButton(
        latest_actions, "باز کردن پوشه", app._open_output_folder,
        icon_key="folder", width=120, height=34,
    ).pack(side="right", padx=(SPACE_XS, 0))
    OutlineButton(
        latest_actions, "کپی مسیر", app._copy_output_dir,
        icon_key="copy", width=100, height=34,
    ).pack(side="right", padx=(SPACE_XS, 0))

    # Paths row
    paths_row = ctk.CTkFrame(content, fg_color="transparent")
    paths_row.pack(fill="x", pady=(0, SPACE_MD))
    paths_row.grid_columnconfigure((0, 1), weight=1)

    app._output_file_field = PathField(
        paths_row, "آخرین فایل", "هنوز فایلی تولید نشده",
        icon_key="file_text", on_copy=app._copy_output_dir, muted=True,
    )
    app._output_file_field.grid(row=0, column=1, sticky="nsew", padx=(SPACE_SM, 0))
    app.last_file_lbl = app._output_file_field.value_lbl

    app._output_folder_field = PathField(
        paths_row, "پوشه خروجی", get_output_dir(),
        on_copy=app._copy_output_dir, on_open=app._open_output_folder,
    )
    app._output_folder_field.grid(row=0, column=0, sticky="nsew", padx=(0, SPACE_SM))
    app.output_dir_lbl = app._output_folder_field.value_lbl

    # Structure hint
    flow_card = AppCard(content, "ساختار پوشه", subtitle="نام‌گذاری خودکار", icon_key="layout", compact=True)
    flow_card.pack(fill="x", pady=(0, SPACE_MD))
    fb = flow_card.body
    path_hint = ctk.CTkFrame(
        fb, corner_radius=8, fg_color=COLORS["surface_secondary"],
        border_width=1, border_color=COLORS["card_border_soft"],
    )
    path_hint.pack(fill="x")
    ctk.CTkLabel(
        path_hint,
        text="output › استان › شهر › منطقه › نوع_معامله.xlsx",
        font=mono_font(11), text_color=COLORS["text_secondary"],
        anchor="e", justify="right",
    ).pack(anchor="e", padx=SPACE_MD, pady=SPACE_SM)
    RtlLabel(
        fb, "بدون نیاز به نام‌گذاری دستی — مسیر بر اساس محدوده و دسته ساخته می‌شود.",
        size=10, muted=True, wraplength=640,
    ).pack(anchor="e", pady=(SPACE_XS, 0))

    app._output_empty = EmptyState(
        content,
        icon_key="folder",
        title="هنوز خروجی‌ای ساخته نشده",
        description="پس از اولین استخراج، فایل‌ها و آمار اینجا نمایش داده می‌شوند.",
        action_text="شروع اولین استخراج",
        on_action=lambda: app._switch_tab("extract"),
    )
    app._output_empty.pack(fill="x", pady=(SPACE_SM, SPACE_MD))

    return page
