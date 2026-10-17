"""مسیرهای اپ استخراج — مستقل از اپ اصلی."""
from __future__ import annotations

import os
import sys


def get_app_root() -> str:
    """ریشه پوشه extractor-app."""
    if getattr(sys, "frozen", False):
        return os.path.dirname(os.path.abspath(sys.executable))
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def get_config_dir() -> str:
    path = os.path.join(get_app_root(), "config")
    os.makedirs(path, exist_ok=True)
    return path


def get_app_data_dir() -> str:
    path = os.path.join(get_config_dir(), "app_data")
    os.makedirs(path, exist_ok=True)
    return path


def get_output_dir(relative_path: str = "") -> str:
    """پوشه output داخل extractor-app."""
    base = os.path.join(get_app_root(), "output")
    os.makedirs(base, exist_ok=True)
    if relative_path:
        return os.path.join(base, relative_path)
    return base


def sanitize_path_segment(name: str) -> str:
    """نام امن برای پوشه/فایل — حذف فاصله‌های اضافه و کاراکترهای نامعتبر ویندوز."""
    text = str(name or "").strip().strip(".")
    for ch in ('/', '\\', ':', '*', '?', '"', '<', '>', '|'):
        text = text.replace(ch, "_")
    return text


def get_resource_path(relative_path: str) -> str:
    """فایل‌های bundled یا کنار exe — اول پوشه نصب، بعد _MEIPASS."""
    rel = relative_path.replace("/", os.sep)
    app_root = get_app_root()
    parent = os.path.dirname(app_root)
    candidates = [
        os.path.join(app_root, rel),
        os.path.join(parent, rel),
        os.path.join(parent, "assets", rel),
    ]
    if not rel.replace("\\", "/").startswith("assets/"):
        candidates.insert(1, os.path.join(app_root, "assets", rel))
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        candidates.append(os.path.join(sys._MEIPASS, rel))
    for path in candidates:
        if os.path.exists(path):
            return path
    return candidates[0]
