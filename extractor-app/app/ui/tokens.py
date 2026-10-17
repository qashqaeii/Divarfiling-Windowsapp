"""Design tokens — مطابق طرح داشبورد فایلینگ دیوار."""
from __future__ import annotations

# Spacing
SPACE_XS = 4
SPACE_SM = 8
SPACE_MD = 12
SPACE_LG = 16
SPACE_XL = 20
SPACE_2XL = 28
SPACE_3XL = 36

# Radii — گوشه‌های نرم مثل طرح
RADIUS_SM = 8
RADIUS_MD = 10
RADIUS_LG = 12
RADIUS_XL = 16

CARD_RADIUS = RADIUS_LG
INPUT_RADIUS = RADIUS_MD
BUTTON_RADIUS = RADIUS_MD

# Sizing
INPUT_HEIGHT = 38
INPUT_HEIGHT_SM = 34
BUTTON_HEIGHT = 42
BUTTON_HEIGHT_SM = 34
BUTTON_HEIGHT_CTA = 48
HEADER_HEIGHT = 64
NAV_HEIGHT = 48
STATUSBAR_HEIGHT = 34
ICON_SIZE = 18
ICON_SIZE_SM = 14
ICON_SIZE_NAV = 16
SIDEBAR_WIDTH = 340

# Layout
MIN_WINDOW_W = 1280
MIN_WINDOW_H = 760
SIDEBAR_RATIO = 0.30
CONTENT_GAP = 14

# Color tokens — (light, dark) — پالت طرح
COLORS = {
    "app_bg": ("#F8F9FB", "#0B0F17"),
    "app_bg_alt": ("#F1F3F7", "#101622"),
    "canvas_bg": ("#F8F9FB", "#0E131D"),
    "surface": ("#FFFFFF", "#141B28"),
    "surface_secondary": ("#F5F6FA", "#1A2332"),
    "card_bg": ("#FFFFFF", "#141B28"),
    "card_bg_soft": ("#F5F6FA", "#1A2332"),
    "card_bg_elevated": ("#FFFFFF", "#171F2E"),
    "card_border": ("#E8EAF0", "#2A3548"),
    "card_border_soft": ("#EFF1F5", "#1E293B"),
    "card_shadow": ("#D8DCE6", "#020617"),
    "text_primary": ("#1A1D26", "#F1F5F9"),
    "text_secondary": ("#5B6475", "#94A3B8"),
    "text_muted": ("#8B93A7", "#64748B"),
    "input_bg": ("#FFFFFF", "#151D2E"),
    "input_border": ("#E0E3EB", "#334155"),
    "input_focus": ("#7C3AED", "#8B5CF6"),
    "primary": ("#7C3AED", "#8B5CF6"),
    "primary_start": ("#7C3AED", "#8B5CF6"),
    "primary_end": ("#8B5CF6", "#A78BFA"),
    "primary_hover": ("#6D28D9", "#7C3AED"),
    "primary_pressed": ("#5B21B6", "#6D28D9"),
    "secondary": ("#0EA5E9", "#38BDF8"),
    "secondary_soft": ("#E0F2FE", "#0C4A6E"),
    "success": ("#16A34A", "#34D399"),
    "success_bg": ("#ECFDF5", "#052E16"),
    "success_border": ("#BBF7D0", "#065F46"),
    "warning": ("#F59E0B", "#FBBF24"),
    "warning_bg": ("#FFFBEB", "#451A03"),
    "warning_border": ("#FDE68A", "#92400E"),
    "error": ("#DC2626", "#F87171"),
    "error_bg": ("#FEF2F2", "#450A0A"),
    "error_border": ("#FECACA", "#991B1B"),
    "info": ("#2563EB", "#60A5FA"),
    "info_bg": ("#EFF6FF", "#172554"),
    "info_border": ("#BFDBFE", "#1E40AF"),
    "brand_soft": ("#F3E8FF", "#2E1065"),
    "brand": ("#7C3AED", "#8B5CF6"),
    "accent": ("#7C3AED", "#8B5CF6"),
    "accent_hover": ("#6D28D9", "#7C3AED"),
    "accent_text": ("#FFFFFF", "#FFFFFF"),
    "accent_glow": ("#E9D5FF", "#312E81"),
    "progress_track": ("#EDEFF5", "#1E293B"),
    "log_bg": ("#FFFFFF", "#0F172A"),
    "log_header": ("#FFFFFF", "#111827"),
    "log_text": ("#1A1D26", "#E2E8F0"),
    "log_title": ("#1A1D26", "#F8FAFC"),
    "log_border": ("#E8EAF0", "#334155"),
    "tab_active": ("#7C3AED", "#8B5CF6"),
    "tab_inactive": ("transparent", "transparent"),
    "nav_rail_bg": ("#FFFFFF", "#151D2E"),
    "header_bg": ("#FFFFFF", "#0B1120"),
    "header_border": ("#EEF0F5", "#1E293B"),
    "header_subtle": ("#F8F9FB", "#111827"),
    "page_hero_bg": ("#FFFFFF", "#111827"),
    "page_hero_border": ("#E8EAF0", "#1E293B"),
    "section_header_bg": ("#FFFFFF", "#151D2E"),
    "hero_glow": ("#F3E8FF", "#2E1065"),
    "stat_pill_bg": ("#FFFFFF", "#151D2E"),
    "statusbar_bg": ("#FFFFFF", "#0B1120"),
    "statusbar_border": ("#EEF0F5", "#1E293B"),
}

LOG_LEVEL_COLORS = {
    "info": ("#7C3AED", "#C4B5FD"),
    "success": ("#16A34A", "#6EE7B7"),
    "warning": ("#F59E0B", "#FCD34D"),
    "error": ("#DC2626", "#FCA5A5"),
    "normal": ("#5B6475", "#94A3B8"),
}

LOG_LEVEL_BADGES = {
    "info": "اطلاع",
    "success": "موفق",
    "warning": "هشدار",
    "error": "خطا",
    "normal": "سیستم",
}

APP_VERSION = "2.15.0"
