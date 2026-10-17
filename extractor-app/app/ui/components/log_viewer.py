"""Live log viewer — مطابق طرح."""
from __future__ import annotations

from typing import Callable, Optional

import customtkinter as ctk

from app.ui.components.buttons import GhostButton, IconButton
from app.ui.components.cards import RtlLabel
from app.ui.tokens import CARD_RADIUS, COLORS, INPUT_RADIUS, LOG_LEVEL_COLORS, SPACE_MD, SPACE_SM, SPACE_XS
from app.ui.typography import font


class LiveLogViewer(ctk.CTkFrame):
    """گزارش زنده عملیات."""

    FILTERS = ("all", "success", "warning", "error")

    def __init__(self, master, on_copy: Optional[Callable] = None, **kw):
        super().__init__(
            master,
            corner_radius=CARD_RADIUS,
            fg_color=COLORS["card_bg"],
            border_width=1,
            border_color=COLORS["card_border"],
            **kw,
        )
        self._filter = "all"
        self._auto_scroll = True
        self._on_copy = on_copy

        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", padx=SPACE_MD, pady=(SPACE_SM, SPACE_XS))

        RtlLabel(header, "گزارش زنده عملیات", size=13, bold=True).pack(side="right")

        tools = ctk.CTkFrame(header, fg_color="transparent")
        tools.pack(side="left")
        IconButton(tools, icon_key="copy", command=self._copy_log, size=28).pack(side="left", padx=(0, 2))
        GhostButton(tools, "پاک‌کردن", self._clear_log, width=72, height=26).pack(side="left")

        # filter pills
        filter_bar = ctk.CTkFrame(self, fg_color=COLORS["surface_secondary"], corner_radius=8)
        filter_bar.pack(fill="x", padx=SPACE_MD, pady=(0, SPACE_SM))
        fi = ctk.CTkFrame(filter_bar, fg_color="transparent")
        fi.pack(fill="x", padx=3, pady=3)
        self._filter_btns: dict[str, ctk.CTkButton] = {}
        labels = {"all": "همه", "success": "موفق", "warning": "هشدار", "error": "خطا"}
        for key in reversed(self.FILTERS):
            btn = ctk.CTkButton(
                fi, text=labels[key], height=26, width=56, corner_radius=6,
                font=font(10, "bold"), command=lambda k=key: self._set_filter(k),
                fg_color="transparent", hover_color=COLORS["card_bg_soft"],
                text_color=COLORS["text_secondary"],
            )
            btn.pack(side="right", padx=1)
            self._filter_btns[key] = btn
        self._paint_filters()

        self.textbox = ctk.CTkTextbox(
            self,
            font=font(12),
            fg_color=COLORS["log_bg"],
            text_color=COLORS["log_text"],
            corner_radius=INPUT_RADIUS,
            activate_scrollbars=True,
            wrap="word",
            border_width=0,
        )
        self.textbox.pack(fill="both", expand=True, padx=SPACE_SM, pady=(0, SPACE_SM))
        self.textbox.configure(state="disabled")
        tb = self.textbox._textbox
        tb.configure(insertofftime=0, insertontime=0)
        for level, color in LOG_LEVEL_COLORS.items():
            c = color[0] if isinstance(color, tuple) else color
            tb.tag_configure(level, foreground=c, justify="right")
        tb.tag_configure("ts", foreground="#8B93A7", justify="right")
        tb.tag_configure("badge", foreground="#7C3AED", justify="right")
        tb.tag_configure("msg", foreground="#1A1D26", justify="right")
        tb.tag_configure("hidden", foreground="#1A1D26")

    @property
    def widget(self) -> ctk.CTkTextbox:
        return self.textbox

    def _paint_filters(self) -> None:
        for key, btn in self._filter_btns.items():
            if key == self._filter:
                btn.configure(
                    fg_color=COLORS["primary"], text_color=COLORS["accent_text"],
                    hover_color=COLORS["primary_hover"],
                )
            else:
                btn.configure(
                    fg_color="transparent", text_color=COLORS["text_secondary"],
                    hover_color=COLORS["card_bg_soft"],
                )

    def _set_filter(self, key: str) -> None:
        self._filter = key
        self._paint_filters()
        tb = self.textbox._textbox
        for i, line_tag in enumerate(getattr(self, "_line_tags", [])):
            # info maps under all
            match = key == "all" or line_tag == key or (key == "success" and line_tag in ("success", "info"))
            if match:
                tb.tag_remove("hidden", f"{i + 1}.0", f"{i + 1}.end")
            else:
                tb.tag_add("hidden", f"{i + 1}.0", f"{i + 1}.end")

    def _clear_log(self) -> None:
        self.textbox.configure(state="normal")
        self.textbox.delete("1.0", "end")
        self.textbox.configure(state="disabled")
        self._line_tags = []

    def _copy_log(self) -> None:
        try:
            content = self.textbox.get("1.0", "end").strip()
            if self._on_copy:
                self._on_copy(content)
            else:
                self.clipboard_clear()
                self.clipboard_append(content)
        except Exception:
            pass

    def prepare_line_tags(self) -> None:
        if not hasattr(self, "_line_tags"):
            self._line_tags = []


LogConsole = LiveLogViewer
