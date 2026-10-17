"""ثابت‌های استخراج — همان نگاشت‌های اپ اصلی."""
from __future__ import annotations

MAX_EXTRACTION_ITEMS = 500
SCHEDULER_MAX_ITEMS = 500

TRANSACTION_TYPES = {
    "فروش مسکونی": {
        "subcategories": [
            {"label": "آپارتمان", "api": "apartment-sell"},
            {"label": "خانه و ویلا", "api": "house-villa-sell"},
            {"label": "کلنگی", "api": "plot-old"},
        ]
    },
    "اجاره مسکونی": {
        "subcategories": [
            {"label": "آپارتمان", "api": "apartment-rent"},
            {"label": "خانه و ویلا", "api": "house-villa-rent"},
        ]
    },
    "فروش اداری و تجاری": {
        "subcategories": [
            {"label": "دفتر کار، اتاق اداری، مطب", "api": "office-sell"},
            {"label": "مغازه و غرفه", "api": "shop-sell"},
            {"label": "صنعتی، کشاورزی، تجاری", "api": "industry-agriculture-business-sell"},
        ]
    },
    "اجاره اداری و تجاری": {
        "subcategories": [
            {"label": "دفتر کار، اتاق اداری، مطب", "api": "office-rent"},
            {"label": "مغازه و غرفه", "api": "shop-rent"},
            {"label": "صنعتی، کشاورزی، تجاری", "api": "industry-agriculture-business-rent"},
        ]
    },
    "پروژه‌های ساخت‌وساز": {
        "subcategories": [
            {"label": "پروژه‌های ساخت‌وساز", "api": "real-estate-services"},
        ]
    },
}

FILE_PREFIX_BY_TRANSACTION = {
    "فروش مسکونی": "فروش",
    "اجاره مسکونی": "اجاره",
    "رهن": "رهن",
    "فروش اداری و تجاری": "فروش اداری تجاری",
    "اجاره اداری و تجاری": "اجاره اداری تجاری",
    "پروژه‌های ساخت‌وساز": "پروژه",
}
