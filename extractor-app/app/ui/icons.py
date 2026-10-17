"""Icon symbols — consistent geometric glyphs (no emoji)."""
from __future__ import annotations

# Navigation
NAV_EXTRACT = "\u25BC"      # ▼
NAV_OUTPUT = "\u25A6"       # ▦
NAV_LICENSE = "\u25C9"      # ◉
NAV_SETTINGS = "\u2699"     # ⚙
NAV_ABOUT = "\u24D8"        # ⓘ

# Actions
PLAY = "\u25B6"             # ▶
STOP = "\u25A0"             # ■
SEARCH = "\u2315"           # ⌕
CLEAR = "\u2715"            # ✕
COPY = "\u2398"             # ⎘
FOLDER = "\u25A1"           # □
FILE = "\u25A4"             # ▤
UPLOAD = "\u21E7"           # ⇧
REFRESH = "\u21BB"          # ↻

# Status
SUCCESS = "\u2713"          # ✓
ERROR = "\u2717"            # ✗
WARNING = "\u0021"          # !
INFO = "\u2139"             # ℹ
LIVE = "\u25CF"             # ●

# Location
PROVINCE = "\u25C7"         # ◇
CITY = "\u25C6"             # ◆
DISTRICT = "\u25A0"         # ■

# Connection
ONLINE = "\u25CF"
OFFLINE = "\u25CB"          # ○
USER = "\u263A"             # ☺

NAV_SCHEDULE = "\u23F1"     # ⏱

NAV_ITEMS = {
    "extract": (NAV_EXTRACT, "استخراج"),
    "output": (NAV_OUTPUT, "خروجی"),
    "schedule": (NAV_SCHEDULE, "زمان‌بندی"),
    "license": (NAV_LICENSE, "لایسنس"),
    "settings": (NAV_SETTINGS, "تنظیمات"),
    "about": (NAV_ABOUT, "درباره"),
}
