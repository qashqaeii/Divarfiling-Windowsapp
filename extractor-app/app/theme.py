"""Design system — backward-compatible re-exports from app.ui."""
from __future__ import annotations

from app.ui.theme import setup_theme
from app.ui.tokens import (
    BUTTON_RADIUS,
    CARD_RADIUS,
    COLORS,
    HEADER_HEIGHT,
    INPUT_HEIGHT,
    INPUT_RADIUS,
    LOG_LEVEL_BADGES,
    LOG_LEVEL_COLORS,
    SPACE_2XL,
    SPACE_LG,
    SPACE_MD,
    SPACE_SM,
    SPACE_XL,
    SPACE_XS,
    STATUSBAR_HEIGHT,
)
from app.ui.typography import (
    FALLBACK_FONT,
    FONT_FAMILY,
    MONO_FAMILY,
    caption,
    font,
    heading,
    mono_font,
)

__all__ = [
    "BUTTON_RADIUS",
    "CARD_RADIUS",
    "COLORS",
    "FALLBACK_FONT",
    "FONT_FAMILY",
    "HEADER_HEIGHT",
    "INPUT_HEIGHT",
    "INPUT_RADIUS",
    "LOG_LEVEL_BADGES",
    "LOG_LEVEL_COLORS",
    "MONO_FAMILY",
    "SPACE_2XL",
    "SPACE_LG",
    "SPACE_MD",
    "SPACE_SM",
    "SPACE_XL",
    "SPACE_XS",
    "STATUSBAR_HEIGHT",
    "caption",
    "font",
    "heading",
    "mono_font",
    "setup_theme",
]
