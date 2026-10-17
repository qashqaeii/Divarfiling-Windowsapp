"""سوییچ حالت استخراج — مطابق طرح."""
from __future__ import annotations

from typing import Callable, Optional

import customtkinter as ctk

from app.ui.tokens import COLORS, RADIUS_MD, SPACE_XS
from app.ui.typography import font


class ExtractionModeSelector(ctk.CTkFrame):
    """[ استخراج گروهی ] [ استخراج تکی ]"""

    def __init__(
        self,
        master,
        *,
        initial: str = "single",
        on_change: Optional[Callable[[str], None]] = None,
        **kw,
    ):
        super().__init__(
            master,
            fg_color="transparent",
            corner_radius=RADIUS_MD,
            border_width=0,
            **kw,
        )
        self._on_change = on_change
        self._mode = initial if initial in ("single", "batch") else "single"

        inner = ctk.CTkFrame(self, fg_color="transparent")
        inner.pack(fill="x", padx=3, pady=3)
        inner.grid_columnconfigure((0, 1), weight=1)

        self._btn_batch = ctk.CTkButton(
            inner, text="استخراج گروهی", height=36, corner_radius=8,
            font=font(12, "bold"), command=lambda: self.set_mode("batch"),
        )
        self._btn_batch.grid(row=0, column=0, sticky="ew", padx=(0, SPACE_XS))

        self._btn_single = ctk.CTkButton(
            inner, text="استخراج تکی", height=36, corner_radius=8,
            font=font(12, "bold"), command=lambda: self.set_mode("single"),
        )
        self._btn_single.grid(row=0, column=1, sticky="ew", padx=(SPACE_XS, 0))

        self._paint()

    @property
    def mode(self) -> str:
        return self._mode

    def set_mode(self, mode: str, *, notify: bool = True) -> None:
        if mode not in ("single", "batch"):
            return
        changed = mode != self._mode
        self._mode = mode
        self._paint()
        if notify and changed and self._on_change:
            self._on_change(mode)

    def _paint(self) -> None:
        active = dict(
            fg_color=COLORS["primary"],
            text_color=COLORS["accent_text"],
            hover_color=COLORS["primary_hover"],
        )
        idle = dict(
            fg_color="transparent",
            text_color=COLORS["text_secondary"],
            hover_color=COLORS["brand_soft"],
        )
        self._btn_single.configure(**(active if self._mode == "single" else idle))
        self._btn_batch.configure(**(active if self._mode == "batch" else idle))
