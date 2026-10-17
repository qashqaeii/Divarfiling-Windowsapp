"""پنل ورود با حساب کاربری — صفحه لایسنس."""
from __future__ import annotations

import customtkinter as ctk

from app.ui.components import DangerOutlineButton, FieldLabel, PrimaryButton, RtlLabel, styled_entry
from app.ui.platform_icons import pack_icon
from app.ui.tokens import CARD_RADIUS, COLORS, SPACE_MD, SPACE_SM, SPACE_XS
from app.widgets import enable_entry_shortcuts


def build_account_login_panel(parent) -> ctk.CTkFrame:
    card = ctk.CTkFrame(
        parent, corner_radius=CARD_RADIUS, fg_color=COLORS["card_bg"],
        border_width=1, border_color=COLORS["card_border"],
    )

    head = ctk.CTkFrame(card, fg_color="transparent")
    head.pack(fill="x", padx=SPACE_MD, pady=(SPACE_MD, SPACE_SM))
    pack_icon(head, "user", size=16, side="right", padx=(SPACE_XS, 0))
    RtlLabel(head, "ورود با حساب کاربری", size=13, bold=True).pack(side="right")
    card._login_status = RtlLabel(head, "", size=10, muted=True)
    card._login_status.pack(side="left")

    body = ctk.CTkFrame(card, fg_color="transparent")
    body.pack(fill="x", padx=SPACE_MD, pady=(0, SPACE_MD))

    FieldLabel(body, "شماره موبایل یا نام کاربری").pack(anchor="e", pady=(0, 4))
    card._login_user = styled_entry(body, placeholder_text="مثلاً ۰۹۱۲…", height=36)
    card._login_user.pack(fill="x", pady=(0, SPACE_SM))
    enable_entry_shortcuts(card._login_user)

    FieldLabel(body, "رمز عبور").pack(anchor="e", pady=(0, 4))
    card._login_pass = styled_entry(body, placeholder_text="رمز عبور", height=36, show="•")
    card._login_pass.pack(fill="x", pady=(0, SPACE_SM))
    enable_entry_shortcuts(card._login_pass)

    card._login_error = RtlLabel(body, "", size=10, wraplength=360)
    card._login_error.configure(text_color=COLORS["error"])
    card._login_error.pack(anchor="e", pady=(0, SPACE_XS))

    btn_row = ctk.CTkFrame(body, fg_color="transparent")
    btn_row.pack(fill="x")
    card._login_btn = PrimaryButton(
        btn_row, "ورود و فعال‌سازی", lambda: None,
        icon_key="log_in", width=158, height=34,
    )
    card._login_btn.pack(side="right")
    card._logout_btn = DangerOutlineButton(
        btn_row, "خروج از حساب", lambda: None,
        icon_key="logout", width=124, height=34,
    )
    card._logout_btn.pack(side="left")
    card._logout_btn.pack_forget()

    sep = ctk.CTkFrame(body, height=1, fg_color=COLORS["card_border"])
    sep.pack(fill="x", pady=(SPACE_SM, SPACE_XS))
    RtlLabel(body, "یا فعال‌سازی با کلید لایسنس (روش قبلی)", size=10, muted=True).pack(anchor="e")

    return card


def set_account_login_error(card: ctk.CTkFrame, message: str) -> None:
    card._login_error.configure(text=message or "")


def set_account_login_busy(card: ctk.CTkFrame, busy: bool) -> None:
    state = "disabled" if busy else "normal"
    card._login_btn.configure(state=state)
    card._login_user.configure(state=state)
    card._login_pass.configure(state=state)


def set_account_session_visible(card: ctk.CTkFrame, logged_in: bool) -> None:
    if logged_in:
        card._login_status.configure(text="وارد شده")
        card._logout_btn.pack(side="left")
    else:
        card._login_status.configure(text="")
        card._logout_btn.pack_forget()


def set_account_login_fields(
    card: ctk.CTkFrame,
    *,
    username: str = "",
    password: str = "",
) -> None:
    card._login_user.delete(0, "end")
    if username:
        card._login_user.insert(0, username)
    card._login_pass.delete(0, "end")
    if password:
        card._login_pass.insert(0, password)
