"""Card and layout components."""
from __future__ import annotations

from typing import Optional

import customtkinter as ctk

from app.ui.platform_icons import PlatformIconCache, pack_icon
from app.ui.tokens import CARD_RADIUS, COLORS, SPACE_MD, SPACE_SM, SPACE_XS
from app.ui.typography import body, card_title, caption, font


class RtlLabel(ctk.CTkLabel):
    """برچسب RTL استاندارد."""

    def __init__(
        self,
        master,
        text: str = "",
        *,
        size: int = 13,
        bold: bool = False,
        muted: bool = False,
        mono: bool = False,
        **kw,
    ):
        kw.setdefault("anchor", "e")
        kw.setdefault("justify", "right")
        if "text_color" not in kw:
            kw["text_color"] = COLORS["text_secondary"] if muted else COLORS["text_primary"]
        f = font(size, "bold" if bold else "normal")
        super().__init__(master, text=text, font=f, **kw)


class FieldLabel(RtlLabel):
    def __init__(self, master, text: str, **kw):
        super().__init__(master, text, size=12, bold=True, muted=True, **kw)


class AppCanvas(ctk.CTkFrame):
    """پس‌زمینه محتوای اصلی."""

    def __init__(self, master, **kw):
        super().__init__(
            master,
            fg_color=COLORS["canvas_bg"],
            corner_radius=0,
            border_width=0,
            **kw,
        )


class AppCard(ctk.CTkFrame):
    """کارت عمومی — بدون accent bar تکراری."""

    def __init__(
        self,
        master,
        title: str = "",
        *,
        subtitle: str = "",
        icon_key: str = "",
        icon: str = "",
        compact: bool = False,
        flat: bool = False,
        **kw,
    ):
        if flat:
            kw.setdefault("fg_color", "transparent")
            kw.setdefault("border_width", 0)
            kw.setdefault("corner_radius", 0)
        else:
            kw.setdefault("corner_radius", CARD_RADIUS)
            kw.setdefault("fg_color", COLORS["card_bg"])
            kw.setdefault("border_width", 1)
            kw.setdefault("border_color", COLORS["card_border"])
        super().__init__(master, **kw)
        if title:
            head = ctk.CTkFrame(self, fg_color="transparent", corner_radius=0)
            head.pack(fill="x")
            row = ctk.CTkFrame(head, fg_color="transparent")
            pad = SPACE_SM if compact else SPACE_MD
            row.pack(fill="x", padx=pad, pady=(SPACE_SM, SPACE_XS))
            if icon_key:
                pack_icon(row, icon_key, size=16, side="right", padx=(SPACE_XS, 0))
            elif icon:
                ctk.CTkLabel(
                    row, text=icon, font=font(11), text_color=COLORS["primary"],
                ).pack(side="right", padx=(SPACE_XS, 0))
            if subtitle:
                RtlLabel(row, subtitle, size=10, muted=True).pack(side="right", fill="x", expand=True)
                ctk.CTkLabel(row, text=" · ", font=caption(10), text_color=COLORS["text_muted"]).pack(side="right")
            RtlLabel(row, title, size=12 if compact else 13, bold=True).pack(side="right")

        pad_body = SPACE_SM if compact else SPACE_MD
        self.body = ctk.CTkFrame(self, fg_color="transparent")
        self.body.pack(fill="both", expand=True, padx=pad_body, pady=(0, pad_body))


class SectionHeader(ctk.CTkFrame):
    """سربرگ بخش در سایدبار."""

    def __init__(self, master, title: str, *, subtitle: str = "", icon_key: str = "", icon: str = "", **kw):
        super().__init__(master, fg_color="transparent", **kw)
        row = ctk.CTkFrame(self, fg_color="transparent")
        row.pack(fill="x", pady=(SPACE_SM, SPACE_XS))
        if icon_key:
            pack_icon(row, icon_key, size=16, side="right", padx=(SPACE_XS, 0))
        elif icon:
            ctk.CTkLabel(row, text=icon, font=font(11), text_color=COLORS["primary"]).pack(
                side="right", padx=(SPACE_XS, 0),
            )
        RtlLabel(row, title, size=12, bold=True).pack(side="right")
        if subtitle:
            RtlLabel(self, subtitle, size=10, muted=True, wraplength=280).pack(anchor="e", pady=(0, SPACE_XS))


class PageHero(ctk.CTkFrame):
    """سربرگ صفحه — فشرده."""

    def __init__(
        self,
        master,
        title: str,
        *,
        eyebrow: str = "",
        subtitle: str = "",
        icon_key: str = "",
        logo_image: Optional[ctk.CTkImage] = None,
        actions_frame: Optional[ctk.CTkFrame] = None,
        **kw,
    ):
        super().__init__(master, fg_color="transparent", **kw)
        row = ctk.CTkFrame(self, fg_color="transparent")
        row.pack(fill="x")

        text_col = ctk.CTkFrame(row, fg_color="transparent")
        text_col.pack(side="right", fill="x", expand=True)

        title_row = ctk.CTkFrame(text_col, fg_color="transparent")
        title_row.pack(fill="x")
        if logo_image:
            chip = ctk.CTkFrame(
                title_row, width=28, height=28, corner_radius=8,
                fg_color=COLORS["brand_soft"], border_width=1, border_color=COLORS["accent_glow"],
            )
            chip.pack(side="right", padx=(SPACE_SM, 0))
            chip.pack_propagate(False)
            ctk.CTkLabel(chip, text="", image=logo_image, fg_color="transparent").place(
                relx=0.5, rely=0.5, anchor="center",
            )
        elif icon_key:
            pack_icon(title_row, icon_key, size=22, side="right", padx=(SPACE_SM, 0))
        RtlLabel(title_row, title, size=15, bold=True).pack(side="right")
        if eyebrow:
            ctk.CTkLabel(title_row, text=" · ", font=caption(10), text_color=COLORS["text_muted"]).pack(side="right")
            RtlLabel(title_row, eyebrow, size=10, muted=True).pack(side="right")

        if subtitle:
            RtlLabel(text_col, subtitle, size=11, muted=True).pack(anchor="e", pady=(2, 0))

        if actions_frame is not None:
            actions_frame.pack(side="left", anchor="w")

        ctk.CTkFrame(self, height=1, fg_color=COLORS["card_border"]).pack(fill="x", pady=(SPACE_SM, 0))


class StatusChip(ctk.CTkFrame):
    """چیپ وضعیت — آیکن/نقطه + برچسب + مقدار."""

    _TONES = {
        "success": "success",
        "brand": "brand",
        "running": "secondary",
        "warning": "warning",
        "error": "error",
        "muted": "text_muted",
        "info": "info",
    }

    def __init__(self, master, label: str, value: str = "—", *, tone: str = "muted", icon_key: str = ""):
        super().__init__(master, fg_color="transparent")
        row = ctk.CTkFrame(self, fg_color="transparent")
        row.pack()
        self._dot = ctk.CTkFrame(row, width=6, height=6, corner_radius=3, fg_color=COLORS["text_muted"])
        # RTL: برچسب → جداکننده → مقدار → آیکن
        RtlLabel(row, label, size=10, muted=True).pack(side="right")
        ctk.CTkLabel(row, text=":", font=caption(9), text_color=COLORS["text_muted"]).pack(side="right", padx=1)
        self._val = RtlLabel(row, value, size=10, bold=True)
        self._val.pack(side="right", padx=(0, 2))
        if icon_key:
            pack_icon(row, icon_key, size=12, side="right", padx=(4, 0))
        else:
            self._dot.pack(side="right", padx=(4, 0))
        self.set_tone(tone)

    def set_value(self, text: str, *, tone: str | None = None) -> None:
        self._val.configure(text=text)
        if tone is not None:
            self.set_tone(tone)

    def set_tone(self, tone: str) -> None:
        key = self._TONES.get(tone, "text_muted")
        self._dot.configure(fg_color=COLORS[key])


class StatusBadge(ctk.CTkFrame):
    """نشان وضعیت رنگی."""

    _STYLES = {
        "success": ("success_bg", "success", "success_border"),
        "warning": ("warning_bg", "warning", "warning_border"),
        "error": ("error_bg", "error", "error_border"),
        "info": ("info_bg", "info", "info_border"),
        "brand": ("brand_soft", "primary", "accent_glow"),
        "muted": ("card_bg_soft", "text_secondary", "card_border"),
    }

    def __init__(self, master, text: str, *, tone: str = "muted", icon_key: str = ""):
        bg, fg, border = self._STYLES.get(tone, self._STYLES["muted"])
        super().__init__(
            master, corner_radius=999, fg_color=COLORS[bg],
            border_width=1, border_color=COLORS[border],
        )
        row = ctk.CTkFrame(self, fg_color="transparent")
        row.pack(padx=8, pady=2)
        if icon_key:
            pack_icon(row, icon_key, size=12, side="right", padx=(4, 0))
        self._lbl = ctk.CTkLabel(
            row, text=text, font=font(10, "bold"), text_color=COLORS[fg],
        )
        self._lbl.pack(side="right")

    def configure_text(self, text: str, *, tone: str | None = None) -> None:
        self._lbl.configure(text=text)
        if tone:
            bg, fg, border = self._STYLES.get(tone, self._STYLES["muted"])
            self.configure(fg_color=COLORS[bg], border_color=COLORS[border])
            self._lbl.configure(text_color=COLORS[fg])


class ChipBadge(ctk.CTkFrame):
    """چیپ اطلاعات کوچک."""

    def __init__(self, master, text: str, *, icon_key: str = "", **kw):
        super().__init__(
            master, corner_radius=6, fg_color=COLORS["surface_secondary"],
            border_width=1, border_color=COLORS["card_border"], **kw,
        )
        row = ctk.CTkFrame(self, fg_color="transparent")
        row.pack(padx=SPACE_SM, pady=2)
        if icon_key:
            pack_icon(row, icon_key, size=12, side="right", padx=(4, 0))
        self._lbl = RtlLabel(row, text, size=11)
        self._lbl.pack(side="right")

    def set_text(self, text: str) -> None:
        self._lbl.configure(text=text)


def detail_row_rtl(parent, label: str) -> ctk.CTkLabel:
    """ردیف برچسب-مقدار: برچسب راست، مقدار در سمت چپِ آن."""
    row = ctk.CTkFrame(parent, fg_color="transparent")
    row.pack(fill="x", pady=4)
    FieldLabel(row, label).pack(side="right")
    val = RtlLabel(row, "—", size=11, bold=True)
    val.pack(side="right", padx=(SPACE_MD, 0))
    return val


def rtl_label_value_row(
    parent,
    label: str,
    value: str = "—",
    *,
    value_size: int = 11,
    bold: bool = True,
    muted_value: bool = False,
    expand_value: bool = False,
) -> RtlLabel:
    """ردیف افقی RTL استاندارد — برچسب راست، مقدار بلافاصله چپِ آن."""
    row = ctk.CTkFrame(parent, fg_color="transparent")
    row.pack(fill="x")
    FieldLabel(row, label).pack(side="right")
    val = RtlLabel(row, value, size=value_size, bold=bold, muted=muted_value)
    if expand_value:
        val.pack(side="right", fill="x", expand=True, padx=(SPACE_MD, 0), anchor="e")
    else:
        val.pack(side="right", padx=(SPACE_SM, 0))
    return val
