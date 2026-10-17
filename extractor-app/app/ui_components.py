"""کامپوننت‌های UI قابل استفاده مجدد — SaaS RTL."""
from __future__ import annotations

import tkinter as tk
import time
from typing import Callable, Optional

import customtkinter as ctk
from PIL import Image, ImageDraw, ImageTk

from app.theme import (
    BUTTON_RADIUS,
    CARD_RADIUS,
    COLORS,
    FONT_FAMILY,
    HEADER_HEIGHT,
    INPUT_HEIGHT,
    INPUT_RADIUS,
    LOG_LEVEL_BADGES,
    LOG_LEVEL_COLORS,
    SPACE_LG,
    SPACE_MD,
    SPACE_SM,
    SPACE_XS,
    SPACE_XL,
    caption,
    font,
    heading,
    mono_font,
)


def _hex_to_rgb(h: str) -> tuple[int, int, int]:
    h = h.lstrip("#")
    return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)


def _lerp(c1: str, c2: str, t: float) -> tuple[int, int, int]:
    r1, g1, b1 = _hex_to_rgb(c1)
    r2, g2, b2 = _hex_to_rgb(c2)
    return (
        int(r1 + (r2 - r1) * t),
        int(g1 + (g2 - g1) * t),
        int(b1 + (b2 - b1) * t),
    )


def create_gradient_image(
    width: int,
    height: int,
    start: str = "#7C3AED",
    end: str = "#A855F7",
    *,
    horizontal: bool = True,
) -> Image.Image:
    w, h = max(2, width), max(2, height)
    img = Image.new("RGB", (w, h))
    px = img.load()
    steps = w if horizontal else h
    for i in range(steps):
        t = i / max(steps - 1, 1)
        rgb = _lerp(start, end, t)
        if horizontal:
            for y in range(h):
                px[i, y] = rgb
        else:
            for x in range(w):
                px[x, i] = rgb
    return img


class GradientImageCache:
    """کش تصاویر گرادیانت برای دکمه‌ها."""

    _cache: dict[tuple, ImageTk.PhotoImage] = {}

    @classmethod
    def get(cls, width: int, height: int, start: str, end: str) -> ImageTk.PhotoImage:
        key = (width, height, start, end)
        if key not in cls._cache:
            img = create_gradient_image(width, height, start, end)
            cls._cache[key] = ImageTk.PhotoImage(img)
        return cls._cache[key]


class RtlLabel(ctk.CTkLabel):
    """برچسب RTL استاندارد."""

    def __init__(self, master, text: str = "", *, size: int = 13, bold: bool = False, muted: bool = False, **kw):
        kw.setdefault("anchor", "e")
        kw.setdefault("justify", "right")
        if "text_color" not in kw:
            if muted:
                color = COLORS["text_secondary"]
            else:
                color = COLORS["text_primary"]
            kw["text_color"] = color
        super().__init__(
            master,
            text=text,
            font=font(size, "bold" if bold else "normal"),
            **kw,
        )


class FieldLabel(RtlLabel):
    def __init__(self, master, text: str, **kw):
        super().__init__(master, text, size=12, bold=True, muted=True, **kw)


class GradientAccentBar(ctk.CTkFrame):
    """خط accent گرادیانت برای hero و section."""

    def __init__(self, master, *, height: int = 3, **kw):
        super().__init__(master, height=height, corner_radius=height // 2, fg_color=COLORS["primary_start"], **kw)
        self.pack_propagate(False)


class PageHero(ctk.CTkFrame):
    """سربرگ تک‌خطی صفحات — eyebrow · title · subtitle."""

    def __init__(
        self,
        master,
        title: str,
        *,
        eyebrow: str = "",
        subtitle: str = "",
        wraplength: int = 520,
        logo_image: Optional[ctk.CTkImage] = None,
        compact: bool = True,
        **kw,
    ):
        super().__init__(master, fg_color="transparent", border_width=0, **kw)

        row = ctk.CTkFrame(self, fg_color="transparent")
        row.pack(fill="x", pady=(0, SPACE_XS))

        inner = ctk.CTkFrame(row, fg_color="transparent")
        inner.pack(fill="x")

        if logo_image is not None:
            chip = ctk.CTkFrame(
                inner, width=28, height=28, corner_radius=8,
                fg_color=COLORS["brand_soft"], border_width=1, border_color=COLORS["accent_glow"],
            )
            chip.pack(side="right", padx=(SPACE_SM, 0))
            chip.pack_propagate(False)
            ctk.CTkLabel(chip, text="", image=logo_image, fg_color="transparent").place(
                relx=0.5, rely=0.5, anchor="center",
            )

        ctk.CTkFrame(
            inner, width=3, height=18, corner_radius=2, fg_color=COLORS["primary_start"],
        ).pack(side="right", padx=(0, SPACE_SM))

        text_row = ctk.CTkFrame(inner, fg_color="transparent")
        text_row.pack(side="right", fill="x", expand=True)

        if subtitle:
            RtlLabel(
                text_row, subtitle, size=10, muted=True, wraplength=wraplength,
            ).pack(side="right", fill="x", expand=True)
            ctk.CTkLabel(
                text_row, text=" · ", font=font(10), text_color=COLORS["text_muted"],
            ).pack(side="right")

        RtlLabel(text_row, title, size=14 if compact else 15, bold=True).pack(side="right")

        if eyebrow:
            ctk.CTkLabel(
                text_row, text=" · ", font=font(10), text_color=COLORS["text_muted"],
            ).pack(side="right")
            RtlLabel(text_row, eyebrow, size=10, muted=True).pack(side="right")

        ctk.CTkFrame(self, height=1, fg_color=COLORS["card_border"]).pack(fill="x")


class AppHeaderBar(ctk.CTkFrame):
    """هدر اصلی برنامه — برند + نوار تب."""

    def __init__(
        self,
        master,
        *,
        brand_name: str,
        brand_tagline: str,
        logo_image: Optional[ctk.CTkImage] = None,
        logo_fallback: str = "د",
        height: int = HEADER_HEIGHT,
        **kw,
    ):
        super().__init__(master, fg_color=COLORS["header_bg"], corner_radius=0, height=height, **kw)
        self.pack_propagate(False)
        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=0)
        self.grid_columnconfigure(2, weight=0)

        nav_host = ctk.CTkFrame(self, fg_color="transparent")
        nav_host.grid(row=0, column=0, sticky="w", padx=(SPACE_LG, SPACE_SM), pady=SPACE_SM)
        self.nav_rail = NavRail(nav_host)
        self.nav_rail.pack(anchor="w")
        self._tab_inner = self.nav_rail._inner

        brand = ctk.CTkFrame(self, fg_color="transparent")
        brand.grid(row=0, column=2, sticky="e", padx=(SPACE_SM, SPACE_LG), pady=SPACE_SM)

        logo = ctk.CTkFrame(
            brand,
            width=34,
            height=34,
            corner_radius=9,
            fg_color=COLORS["brand_soft"],
            border_width=1,
            border_color=COLORS["accent_glow"],
        )
        logo.pack(side="right", padx=(SPACE_SM, 0))
        logo.pack_propagate(False)
        if logo_image:
            ctk.CTkLabel(logo, text="", image=logo_image, fg_color="transparent").place(
                relx=0.5, rely=0.5, anchor="center",
            )
        else:
            ctk.CTkLabel(
                logo,
                text=logo_fallback,
                font=font(14, "bold"),
                text_color=COLORS["accent_text"],
                fg_color=COLORS["primary_start"],
            ).place(relx=0.5, rely=0.5, anchor="center")

        title_row = ctk.CTkFrame(brand, fg_color="transparent")
        title_row.pack(side="right", padx=(SPACE_SM, 0))
        if brand_tagline:
            RtlLabel(title_row, brand_tagline, size=10, muted=True).pack(side="right")
            ctk.CTkLabel(
                title_row, text=" · ", font=font(10), text_color=COLORS["text_muted"],
            ).pack(side="right")
        RtlLabel(title_row, brand_name, size=15, bold=True).pack(side="right")


class NavRail(ctk.CTkFrame):
    """نوار segmented برای تب‌های header."""

    def __init__(self, master, **kw):
        super().__init__(
            master,
            fg_color=COLORS["nav_rail_bg"],
            corner_radius=10,
            border_width=1,
            border_color=COLORS["card_border"],
            **kw,
        )
        self._inner = ctk.CTkFrame(self, fg_color="transparent")
        self._inner.pack(padx=3, pady=3)


class AppCanvas(ctk.CTkFrame):
    """پس‌زمینه نرم محتوای اصلی."""

    def __init__(self, master, **kw):
        super().__init__(
            master,
            fg_color=COLORS["canvas_bg"],
            corner_radius=CARD_RADIUS,
            border_width=1,
            border_color=COLORS["card_border_soft"],
            **kw,
        )


class DashboardCard(ctk.CTkFrame):
    """کارت premium با accent bar."""

    def __init__(
        self,
        master,
        title: str = "",
        *,
        subtitle: str = "",
        accent: bool = False,
        **kw,
    ):
        border = COLORS["primary_start"] if accent else COLORS["card_border"]
        super().__init__(
            master,
            corner_radius=CARD_RADIUS,
            fg_color=COLORS["card_bg"],
            border_width=1,
            border_color=border,
            **kw,
        )
        shell = ctk.CTkFrame(self, fg_color="transparent")
        shell.pack(fill="both", expand=True)

        if accent:
            ctk.CTkFrame(
                shell, width=4, corner_radius=2, fg_color=COLORS["primary_start"],
            ).pack(side="right", fill="y", padx=(0, 0), pady=0)

        content = ctk.CTkFrame(shell, fg_color="transparent")
        content.pack(side="right", fill="both", expand=True)

        if title:
            head = ctk.CTkFrame(
                content,
                fg_color=COLORS["section_header_bg"],
                corner_radius=0,
            )
            head.pack(fill="x")
            title_row = ctk.CTkFrame(head, fg_color="transparent")
            title_row.pack(fill="x", padx=SPACE_MD, pady=SPACE_SM)
            if accent:
                dot = ctk.CTkFrame(
                    title_row, width=7, height=7, corner_radius=4, fg_color=COLORS["primary_end"],
                )
                dot.pack(side="right", padx=(SPACE_SM, 0), pady=4)
            if subtitle:
                RtlLabel(
                    title_row, subtitle, size=10, muted=True, wraplength=280,
                ).pack(side="right", fill="x", expand=True)
                ctk.CTkLabel(
                    title_row, text=" · ", font=font(10), text_color=COLORS["text_muted"],
                ).pack(side="right")
            RtlLabel(title_row, title, size=13, bold=True).pack(side="right")
            ctk.CTkFrame(head, height=1, fg_color=COLORS["card_border"]).pack(fill="x")

        self.body = ctk.CTkFrame(content, fg_color="transparent")
        self.body.pack(fill="both", expand=True, padx=SPACE_MD, pady=(0, SPACE_MD))


class GradientButton(ctk.CTkButton):
    """دکمه CTA اصلی."""

    def __init__(
        self,
        master,
        text: str,
        command: Optional[Callable] = None,
        *,
        width: int = 140,
        height: int = 44,
        **kw,
    ):
        super().__init__(
            master,
            text=text,
            command=command,
            width=width,
            height=height,
            corner_radius=BUTTON_RADIUS,
            font=font(13, "bold"),
            fg_color=COLORS["primary_start"],
            hover_color=COLORS["primary_hover"],
            text_color=COLORS["accent_text"],
            border_width=0,
            **kw,
        )


class GhostButton(ctk.CTkButton):
    def __init__(self, master, text: str, command=None, *, width=120, height=40, **kw):
        kw.setdefault("font", font(12, "bold"))
        super().__init__(
            master,
            text=text,
            command=command,
            width=width,
            height=height,
            corner_radius=BUTTON_RADIUS,
            fg_color=COLORS["brand_soft"],
            hover_color=COLORS["accent_glow"],
            text_color=COLORS["primary_start"],
            border_width=0,
            **kw,
        )


class OutlineButton(ctk.CTkButton):
    def __init__(self, master, text: str, command=None, *, width=120, height=44, **kw):
        kw.setdefault("font", font(13, "bold"))
        super().__init__(
            master,
            text=text,
            command=command,
            width=width,
            height=height,
            corner_radius=BUTTON_RADIUS,
            fg_color="transparent",
            hover_color=COLORS["card_bg_soft"],
            text_color=COLORS["text_primary"],
            border_width=1,
            border_color=COLORS["card_border"],
            **kw,
        )


class DangerOutlineButton(ctk.CTkButton):
    def __init__(self, master, text: str, command=None, *, width=120, height=44, **kw):
        kw.setdefault("font", font(12))
        super().__init__(
            master,
            text=text,
            command=command,
            width=width,
            height=height,
            corner_radius=BUTTON_RADIUS,
            fg_color="transparent",
            hover_color=COLORS["error_bg"],
            text_color=COLORS["error"],
            border_width=1,
            border_color=COLORS["error_border"],
            **kw,
        )


class TabPill(ctk.CTkButton):
    def __init__(self, master, text: str, command=None, **kw):
        super().__init__(
            master,
            text=text,
            command=command,
            width=84,
            height=30,
            corner_radius=8,
            font=font(11, "bold"),
            fg_color="transparent",
            hover_color=COLORS["card_bg_soft"],
            text_color=COLORS["text_secondary"],
            **kw,
        )

    def set_active(self, active: bool) -> None:
        if active:
            self.configure(
                fg_color=COLORS["primary_start"],
                text_color=COLORS["accent_text"],
                hover_color=COLORS["primary_hover"],
            )
        else:
            self.configure(
                fg_color="transparent",
                text_color=COLORS["text_secondary"],
                hover_color=COLORS["card_bg_soft"],
            )


class StatPill(ctk.CTkFrame):
    """نشانگر آماری کوچک در هدر."""

    def __init__(self, master, label: str, value: str = "—", *, accent: str = "brand"):
        super().__init__(master, corner_radius=10, fg_color=COLORS["stat_pill_bg"],
                         border_width=1, border_color=COLORS["card_border"])
        inner = ctk.CTkFrame(self, fg_color="transparent")
        inner.pack(padx=SPACE_MD, pady=SPACE_SM)
        self._val = RtlLabel(inner, value, size=13, bold=True)
        self._val.pack(anchor="e")
        RtlLabel(inner, label, size=10, muted=True).pack(anchor="e")

    def set_value(self, text: str) -> None:
        self._val.configure(text=text)


class StatusChip(ctk.CTkFrame):
    """چیپ وضعیت مینیمال — نقطه رنگی + برچسب + مقدار."""

    _TONES = {
        "success": "success",
        "brand": "brand",
        "running": "secondary",
        "warning": "warning",
        "error": "error",
        "muted": "text_muted",
    }

    def __init__(self, master, label: str, value: str = "—", *, tone: str = "muted"):
        super().__init__(master, fg_color="transparent")
        row = ctk.CTkFrame(self, fg_color="transparent")
        row.pack()
        self._dot = ctk.CTkFrame(row, width=5, height=5, corner_radius=3,
                                 fg_color=COLORS["text_muted"])
        self._dot.pack(side="right", padx=(4, 0))
        self._val = RtlLabel(row, value, size=10, bold=True)
        self._val.pack(side="right")
        ctk.CTkLabel(
            row, text="·", font=font(9), text_color=COLORS["text_muted"],
        ).pack(side="right", padx=1)
        RtlLabel(row, label, size=10, muted=True).pack(side="right")
        self.set_tone(tone)

    def set_value(self, text: str, *, tone: Optional[str] = None) -> None:
        self._val.configure(text=text)
        if tone is not None:
            self.set_tone(tone)

    def set_tone(self, tone: str) -> None:
        key = self._TONES.get(tone, "text_muted")
        self._dot.configure(fg_color=COLORS[key])


class GradientProgressBar(ctk.CTkFrame):
    """نوار پیشرفت با گرادیانت."""

    def __init__(self, master, height: int = 14, **kw):
        super().__init__(
            master,
            height=height + 8,
            corner_radius=height // 2 + 4,
            fg_color=COLORS["progress_track"],
            border_width=0,
            **kw,
        )
        self.pack_propagate(False)
        self._height = height
        self._value = 0.0
        self._canvas = tk.Canvas(
            self, height=height, highlightthickness=0, bd=0, bg="#E2E8F0",
        )
        self._canvas.pack(fill="x", expand=True, padx=4, pady=4)
        self._photo: Optional[ImageTk.PhotoImage] = None
        self.bind("<Configure>", lambda _e: self._redraw())
        self.after(50, self._redraw)

    def set(self, value: float) -> None:
        self._value = max(0.0, min(1.0, value))
        self._redraw()

    def _redraw(self) -> None:
        self._canvas.delete("all")
        w = self._canvas.winfo_width()
        h = self._height
        if w < 4:
            return
        self._canvas.configure(height=h)
        track = create_gradient_image(w, h, "#E2E8F0", "#CBD5E1")
        self._track_photo = ImageTk.PhotoImage(track)
        self._canvas.create_image(0, 0, anchor="nw", image=self._track_photo)
        fill_w = max(0, int(w * self._value))
        if fill_w > 2:
            grad = create_gradient_image(fill_w, h, "#6366F1", "#8B5CF6")
            self._photo = ImageTk.PhotoImage(grad)
            self._canvas.create_image(0, 0, anchor="nw", image=self._photo)


class LogConsole(ctk.CTkFrame):
    """پنل لاگ premium."""

    def __init__(self, master, **kw):
        super().__init__(
            master,
            corner_radius=CARD_RADIUS,
            fg_color=COLORS["log_header"],
            border_width=1,
            border_color=COLORS["log_border"],
            **kw,
        )
        header = ctk.CTkFrame(self, fg_color=COLORS["section_header_bg"], corner_radius=0)
        header.pack(fill="x")
        header_inner = ctk.CTkFrame(header, fg_color="transparent")
        header_inner.pack(fill="x", padx=SPACE_MD, pady=SPACE_SM)
        title_row = ctk.CTkFrame(header_inner, fg_color="transparent")
        title_row.pack(fill="x")
        live = ctk.CTkFrame(title_row, fg_color=COLORS["success_bg"], corner_radius=999)
        live.pack(side="right", padx=(SPACE_SM, 0))
        ctk.CTkLabel(
            live,
            text=" LIVE ",
            font=font(8, "bold"),
            text_color=COLORS["success"],
        ).pack()
        RtlLabel(
            title_row, "گزارش زنده عملیات", size=13, bold=True,
            text_color=COLORS["log_title"],
        ).pack(side="right")
        ctk.CTkFrame(header, height=1, fg_color=COLORS["log_border"]).pack(fill="x")

        self.textbox = ctk.CTkTextbox(
            self,
            font=font(13),
            fg_color=COLORS["log_bg"],
            text_color=COLORS["log_text"],
            corner_radius=INPUT_RADIUS,
            activate_scrollbars=True,
            wrap="word",
            border_width=1,
            border_color=COLORS["card_border_soft"],
        )
        self.textbox.pack(fill="both", expand=True, padx=SPACE_SM, pady=(0, SPACE_SM))
        self.textbox.configure(state="disabled")
        tb = self.textbox._textbox
        tb.configure(insertofftime=0, insertontime=0)
        for level, color in LOG_LEVEL_COLORS.items():
            c = color[0] if isinstance(color, tuple) else color
            tb.tag_configure(level, foreground=c, justify="right")
        tb.tag_configure("ts", foreground="#64748B", justify="right")
        tb.tag_configure("badge", foreground="#6366F1", justify="right")
        tb.tag_configure("msg", foreground="#0F172A", justify="right")

    @property
    def widget(self) -> ctk.CTkTextbox:
        return self.textbox


def styled_entry(parent, **kwargs) -> ctk.CTkEntry:
    defaults = {
        "justify": "right",
        "font": font(14),
        "height": INPUT_HEIGHT,
        "corner_radius": INPUT_RADIUS,
        "border_color": COLORS["input_border"],
        "fg_color": COLORS["input_bg"],
        "border_width": 1,
    }
    defaults.update(kwargs)
    return ctk.CTkEntry(parent, **defaults)


def style_scrollable(frame: ctk.CTkScrollableFrame) -> None:
    """اسکرول‌بار + بهینه‌سازی سرعت CTkScrollableFrame."""
    try:
        frame._scrollbar.configure(
            width=14,
            fg_color=COLORS["card_bg_soft"],
            button_color=COLORS["primary_start"],
            button_hover_color=COLORS["primary_hover"],
        )
        _patch_ctk_scrollable_performance(frame)
    except Exception:
        pass


def _patch_ctk_scrollable_performance(frame: ctk.CTkScrollableFrame) -> None:
    """حذف bind_all دائمی و debounce scrollregion."""
    configure_after: dict[int, Optional[str]] = {"id": None}

    def _schedule(_event=None) -> None:
        aid = configure_after["id"]
        if aid:
            try:
                frame.after_cancel(aid)
            except Exception:
                pass
        configure_after["id"] = frame.after(48, _update_region)

    def _update_region() -> None:
        configure_after["id"] = None
        try:
            bbox = frame._parent_canvas.bbox("all")
            if bbox:
                frame._parent_canvas.configure(scrollregion=bbox)
        except Exception:
            pass

    def _fast_wheel(event) -> None:
        if not frame.check_if_master_is_canvas(event.widget):
            return
        try:
            if frame._parent_canvas.yview() == (0.0, 1.0):
                return
        except Exception:
            return
        step = -int(event.delta / 2)
        if step:
            frame._parent_canvas.yview_scroll(step, "units")

    try:
        frame.unbind_all("<MouseWheel>")
        frame.unbind_all("<KeyPress-Shift_L>")
        frame.unbind_all("<KeyPress-Shift_R>")
        frame.unbind_all("<KeyRelease-Shift_L>")
        frame.unbind_all("<KeyRelease-Shift_R>")
    except Exception:
        pass

    try:
        frame.unbind("<Configure>")
    except Exception:
        pass
    frame.bind("<Configure>", _schedule, add="+")

    canvas = frame._parent_canvas
    canvas.bind("<Enter>", lambda _e: canvas.bind_all("<MouseWheel>", _fast_wheel, add="+"), add="+")
    canvas.bind(
        "<Leave>",
        lambda _e: canvas.after(80, lambda: canvas.unbind_all("<MouseWheel>")),
        add="+",
    )


_DROPDOWN_ITEM_HEIGHT = 32
_DROPDOWN_MAX_VISIBLE = 8
_DROPDOWN_POPUP_PADDING = 4
_DROPDOWN_WINDOW_MARGIN = 10
_DROPDOWN_MAX_WIDTH = 310


def _theme_color(key: str) -> str:
    val = COLORS[key]
    return val[0] if isinstance(val, tuple) else str(val)


class ScrollableDropdownPopup:
    """منوی بازشونده با اسکرول — همیشه داخل پنجره اپ."""

    _active: Optional["ScrollableDropdownPopup"] = None

    def __init__(self, combo: "RtlComboBox") -> None:
        self._combo = combo
        self._top: Optional[tk.Toplevel] = None
        self._listbox: Optional[tk.Listbox] = None
        self._outside_bind_id: Optional[str] = None
        self._scroll_after_id: Optional[str] = None
        self._outside_bind_after_id: Optional[str] = None
        self._opened_at: float = 0.0

    @staticmethod
    def _measure_combo_width(combo: "RtlComboBox") -> int:
        combo.update_idletasks()
        try:
            scaled = int(combo._apply_widget_scaling(int(combo._current_width)))
            if scaled >= 48:
                return min(scaled, _DROPDOWN_MAX_WIDTH)
        except Exception:
            pass
        w = combo.winfo_width()
        if w >= 48:
            return min(w, _DROPDOWN_MAX_WIDTH)
        parent = combo.master
        for _ in range(5):
            if parent is None:
                break
            pw = parent.winfo_width()
            if pw >= 48:
                return min(pw - 20, _DROPDOWN_MAX_WIDTH)
            parent = getattr(parent, "master", None)
        return 260

    @staticmethod
    def _scroll_to_item(listbox: tk.Listbox, idx: int) -> None:
        try:
            if listbox.winfo_exists() and idx >= 0:
                listbox.see(idx)
        except tk.TclError:
            pass

    @classmethod
    def _calc_geometry(cls, combo: "RtlComboBox", values: list[str]) -> tuple[int, int, int, int]:
        combo.update_idletasks()
        root = combo.winfo_toplevel()
        root.update_idletasks()

        win_x = root.winfo_rootx()
        win_y = root.winfo_rooty()
        win_w = max(root.winfo_width(), 1)
        win_h = max(root.winfo_height(), 1)

        combo_x = combo.winfo_rootx()
        combo_y = combo.winfo_rooty()
        combo_w = cls._measure_combo_width(combo)
        combo_h = max(combo.winfo_height(), INPUT_HEIGHT)
        margin = _DROPDOWN_WINDOW_MARGIN
        win_right = win_x + win_w - margin
        win_left = win_x + margin

        width = min(combo_w, _DROPDOWN_MAX_WIDTH, win_w - 2 * margin)
        width = max(100, width)

        preferred_items = min(len(values), _DROPDOWN_MAX_VISIBLE)
        preferred_h = preferred_items * _DROPDOWN_ITEM_HEIGHT + _DROPDOWN_POPUP_PADDING
        min_h = _DROPDOWN_ITEM_HEIGHT + _DROPDOWN_POPUP_PADDING

        space_below = win_y + win_h - (combo_y + combo_h) - margin
        space_above = combo_y - win_y - margin
        open_up = space_below < min_h and space_above > space_below

        if open_up:
            avail = max(min_h, space_above)
        else:
            avail = max(min_h, space_below)

        height = min(preferred_h, avail)
        inner = height - _DROPDOWN_POPUP_PADDING
        visible_items = max(1, min(len(values), inner // _DROPDOWN_ITEM_HEIGHT))
        height = visible_items * _DROPDOWN_ITEM_HEIGHT + _DROPDOWN_POPUP_PADDING

        if open_up:
            y = combo_y - height
        else:
            y = combo_y + combo_h
        y = max(win_y + margin, min(y, win_y + win_h - height - margin))

        # لبه راست منو = لبه راست combobox (مناسب سایدبار RTL)
        combo_right = combo_x + combo_w
        x = combo_right - width
        if x < win_left:
            x = win_left
        if x + width > win_right:
            x = win_right - width
        x = max(win_left, x)

        return x, y, width, height

    @classmethod
    def open_for(cls, combo: "RtlComboBox") -> None:
        if cls._active is not None:
            cls._active.close()
        popup = cls(combo)
        cls._active = popup
        popup.show()

    def show(self) -> None:
        combo = self._combo
        values = list(combo._values)
        if not values:
            return

        x, y, width, height = self._calc_geometry(combo, values)

        root = combo.winfo_toplevel()
        top = tk.Toplevel(root)
        top.withdraw()
        top.overrideredirect(True)
        top.attributes("-topmost", True)
        top.resizable(False, False)
        top.geometry(f"{width}x{height}+{x}+{y}")
        self._top = top
        self._opened_at = time.monotonic()

        border_c = _theme_color("card_border")
        bg_c = _theme_color("card_bg")
        hover_c = _theme_color("brand_soft")
        text_c = _theme_color("text_primary")

        shell = tk.Frame(top, width=width, height=height, bg=border_c, bd=0)
        shell.pack_propagate(False)
        shell.pack(fill="both", expand=False)

        inner = tk.Frame(shell, bg=bg_c)
        inner.pack(fill="both", expand=True, padx=1, pady=1)

        list_wrap = tk.Frame(inner, bg=bg_c)
        list_wrap.pack(fill="both", expand=True, padx=2, pady=2)

        scrollbar = tk.Scrollbar(list_wrap, orient="vertical", width=12)
        listbox = tk.Listbox(
            list_wrap,
            font=(FONT_FAMILY, 13),
            activestyle="none",
            highlightthickness=0,
            bd=0,
            bg=bg_c,
            fg=text_c,
            selectbackground=hover_c,
            selectforeground=text_c,
            yscrollcommand=scrollbar.set,
            exportselection=False,
        )
        scrollbar.config(command=listbox.yview)
        scrollbar.pack(side="right", fill="y")
        listbox.pack(side="left", fill="both", expand=True)
        self._listbox = listbox

        current = combo.get()
        current_idx = -1
        for idx, value in enumerate(values):
            listbox.insert("end", f"  {value}")
            if value == current:
                current_idx = idx

        if current_idx >= 0:
            listbox.selection_set(current_idx)
            self._scroll_after_id = combo.after_idle(
                lambda i=current_idx: self._scroll_to_item(listbox, i)
            )

        def _on_pick(event: tk.Event) -> None:
            idx = listbox.nearest(event.y)
            if 0 <= idx < len(values):
                self._select(values[idx])

        listbox.bind("<ButtonRelease-1>", _on_pick)

        top.bind("<Escape>", lambda _e: self.close())
        top.update_idletasks()
        top.deiconify()
        top.lift()

        def _arm_outside_bind() -> None:
            self._outside_bind_id = root.bind(
                "<ButtonRelease-1>", self._on_outside_click, add="+",
            )

        self._outside_bind_after_id = combo.after(120, _arm_outside_bind)

    def _select(self, value: str) -> None:
        self._combo._dropdown_callback(value)
        self.close()

    @staticmethod
    def _widget_hits(widget, x: int, y: int) -> bool:
        try:
            if not widget.winfo_exists():
                return False
            wx, wy = widget.winfo_rootx(), widget.winfo_rooty()
            ww, wh = widget.winfo_width(), widget.winfo_height()
            return wx <= x <= wx + ww and wy <= y <= wy + wh
        except tk.TclError:
            return False

    def _on_outside_click(self, event: tk.Event) -> None:
        if time.monotonic() - self._opened_at < 0.15:
            return
        if self._top is None or not self._top.winfo_exists():
            self.close()
            return
        x, y = event.x_root, event.y_root
        if self._widget_hits(self._top, x, y):
            return
        if self._widget_hits(self._combo, x, y):
            return
        w = event.widget
        while w is not None:
            if w in (self._top, self._combo):
                return
            w = getattr(w, "master", None)
        self.close()

    def close(self) -> None:
        if ScrollableDropdownPopup._active is self:
            ScrollableDropdownPopup._active = None
        if self._scroll_after_id is not None:
            try:
                self._combo.after_cancel(self._scroll_after_id)
            except Exception:
                pass
            self._scroll_after_id = None
        if self._outside_bind_after_id is not None:
            try:
                self._combo.after_cancel(self._outside_bind_after_id)
            except Exception:
                pass
            self._outside_bind_after_id = None
        if self._outside_bind_id is not None:
            try:
                root = self._combo.winfo_toplevel()
                root.unbind("<ButtonRelease-1>", self._outside_bind_id)
            except Exception:
                pass
            self._outside_bind_id = None
        if self._top is not None:
            try:
                self._top.destroy()
            except Exception:
                pass
            self._top = None
        self._listbox = None


def _patch_dropdown_menu_rtl(menu) -> None:
    """منوی بازشونده ComboBox — فونت فارسی و تراز راست."""

    def rtl_add_menu_commands() -> None:
        menu.delete(0, "end")
        width = max(getattr(menu, "_min_character_width", 18), 24)
        for value in menu._values:
            label = value.rjust(width) if len(value) < width else value
            menu.add_command(
                label=label,
                command=lambda v=value: menu._button_callback(v),
            )

    menu._add_menu_commands = rtl_add_menu_commands
    menu._add_menu_commands()


def apply_combobox_rtl(combo: ctk.CTkComboBox) -> None:
    """فونت فارسی + تراز راست برای ComboBox و منوی بازشونده."""
    f = font(14)
    try:
        combo.configure(font=f, dropdown_font=f)
    except Exception:
        combo.configure(font=f)
    try:
        combo._entry.configure(justify="right", font=f)
        combo._entry._entry.configure(justify="right", font=(FONT_FAMILY, 14))
    except Exception:
        pass
    try:
        combo._dropdown_menu.configure(font=f)
        _patch_dropdown_menu_rtl(combo._dropdown_menu)
    except Exception:
        pass


class RtlComboBox(ctk.CTkComboBox):
    """ComboBox با فونت فارسی و RTL."""

    def __init__(self, master, **kwargs):
        f = font(14)
        kwargs.setdefault("font", f)
        kwargs.setdefault("dropdown_font", f)
        super().__init__(master, **kwargs)
        self.after_idle(lambda: apply_combobox_rtl(self))

    def _open_dropdown_menu(self) -> None:
        if str(self._state).lower() == "disabled" or not self._values:
            return
        ScrollableDropdownPopup.open_for(self)

    def configure(self, **kwargs):
        super().configure(**kwargs)
        if "values" in kwargs:
            self.after_idle(lambda: apply_combobox_rtl(self))


def styled_combobox(parent, **kwargs) -> RtlComboBox:
    defaults = {
        "font": font(14),
        "height": INPUT_HEIGHT,
        "corner_radius": INPUT_RADIUS,
        "border_color": COLORS["input_border"],
        "fg_color": COLORS["input_bg"],
        "button_color": COLORS["primary_start"],
        "button_hover_color": COLORS["primary_hover"],
        "dropdown_fg_color": COLORS["card_bg"],
        "dropdown_hover_color": COLORS["brand_soft"],
        "dropdown_text_color": COLORS["text_primary"],
        "dropdown_font": font(14),
    }
    defaults.update(kwargs)
    return RtlComboBox(parent, **defaults)


def detail_row_rtl(parent, label: str) -> ctk.CTkLabel:
    """ردیف جزئیات RTL: برچسب راست، مقدار با تراز راست."""
    row = ctk.CTkFrame(parent, fg_color="transparent")
    row.pack(fill="x", pady=5)
    lbl = FieldLabel(row, label)
    lbl.pack(side="right")
    val = RtlLabel(row, "—", size=11, bold=True)
    val.pack(side="right", fill="x", expand=True, padx=(SPACE_MD, 0))
    return val
