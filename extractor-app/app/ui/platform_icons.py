"""آیکن‌های PNG پلتفرم — همان فایل‌های static/icons جنگو."""
from __future__ import annotations

import os
from typing import Dict, Optional

import customtkinter as ctk
from PIL import Image

from app.paths import get_resource_path

# نگاشت کلید UI → نام فایل (منبع: django/shop/decor_icons.py)
PLATFORM_ICON_FILES: Dict[str, str] = {
    # ناوبری
    "extract": "download.png",
    "output": "folder.png",
    "license": "handshake.png",
    "settings": "settings.png",
    "about": "help_center.png",
    "help_center": "help_center.png",
    # عملیات
    "search": "search.png",
    "copy": "copy.png",
    "upload": "upload.png",
    "download": "download.png",
    "folder": "folder.png",
    "rocket": "rocket.png",
    "stop": "rotate_ccw.png",
    "refresh": "rotate_ccw.png",
    "save": "clipboard_list.png",
    "clear": "rotate_ccw.png",
    # داده و مکان
    "database": "database.png",
    "map_pin": "map_pin.png",
    "building": "building.png",
    "layout": "layout_grid.png",
    "filter": "filter.png",
    "calendar": "calendar.png",
    "timer": "timer.png",
    "automation": "automation.png",
    "bar_chart": "bar_chart.png",
    "file_text": "file_text.png",
    "clipboard": "clipboard_list.png",
    "list": "list_todo.png",
    # وضعیت و کاربر
    "bell": "bell.png",
    "user": "user.png",
    "sparkles": "sparkles.png",
    "log_in": "user.png",
    "logout": "rotate_ccw.png",
    "zap": "zap.png",
    "coins": "coins.png",
    # لینک و تم
    "external_link": "external_link.png",
    "phone": "phone.png",
    "theme": "theme_switch.png",
    "api": "api_documentation.png",
}

NAV_ICON_KEYS: Dict[str, str] = {
    "extract": "extract",
    "output": "output",
    "schedule": "automation",
    "license": "license",
    "settings": "settings",
    "about": "about",
}


class PlatformIconCache:
    """کش CTkImage برای آیکن‌های PNG."""

    _cache: Dict[tuple[str, int], ctk.CTkImage] = {}
    _refs: list[ctk.CTkImage] = []

    @classmethod
    def get(cls, name: str, size: int = 16) -> Optional[ctk.CTkImage]:
        key = (name, size)
        if key in cls._cache:
            return cls._cache[key]
        filename = PLATFORM_ICON_FILES.get(name)
        if not filename:
            return None
        path = get_resource_path(os.path.join("assets", "icons", filename))
        if not os.path.isfile(path):
            path = get_resource_path(os.path.join("icons", filename))
        if not os.path.isfile(path):
            return None
        try:
            img = Image.open(path).convert("RGBA")
            image = ctk.CTkImage(light_image=img, dark_image=img, size=(size, size))
            cls._cache[key] = image
            cls._refs.append(image)
            return image
        except Exception:
            return None

    @classmethod
    def nav_icon(cls, tab_key: str, size: int = 16) -> Optional[ctk.CTkImage]:
        icon_key = NAV_ICON_KEYS.get(tab_key, tab_key)
        return cls.get(icon_key, size=size)


def pack_icon(
    parent,
    icon_key: str,
    *,
    size: int = 16,
    side: str = "right",
    padx=0,
    pady=0,
) -> Optional[ctk.CTkLabel]:
    """چسباندن آیکن PNG به یک فریم."""
    image = PlatformIconCache.get(icon_key, size)
    if image is None:
        return None
    lbl = ctk.CTkLabel(parent, text="", image=image, fg_color="transparent")
    lbl.pack(side=side, padx=padx, pady=pady)
    lbl._icon_image = image
    return lbl


def button_icon_kwargs(
    text: str,
    *,
    icon_key: str = "",
    icon_size: int = 16,
    compound: str = "right",
) -> dict:
    """پارامترهای image برای دکمه‌های CTk."""
    image = PlatformIconCache.get(icon_key, icon_size) if icon_key else None
    if image is None:
        return {"text": text}
    return {"text": text, "image": image, "compound": compound}
