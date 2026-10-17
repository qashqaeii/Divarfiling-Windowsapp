"""فیلترهای پیشرفته استخراج — پارس و کمک‌تابع‌ها."""
from __future__ import annotations

from typing import Any, Dict, FrozenSet, Optional

try:
    from advertiser_signal import (
        ADVERTISER_FILTER_LABELS,
        ADVERTISER_FILTER_VALUES,
        normalize_filter_value,
    )
except ImportError:  # pragma: no cover
    ADVERTISER_FILTER_VALUES = frozenset({"all", "consultant", "personal", "genuine_personal"})
    ADVERTISER_FILTER_LABELS = {
        "all": "همه آگهی‌ها",
        "consultant": "فقط مشاور",
        "personal": "شخصی",
        "genuine_personal": "مالک واقعی",
    }

    def normalize_filter_value(value: str = "") -> str:
        key = str(value or "").strip().lower()
        return key if key in ADVERTISER_FILTER_VALUES else "all"

_EN_DIGITS = str.maketrans("۰۱۲۳۴۵۶۷۸۹", "0123456789")

ADVERTISER_FILTER_OPTIONS = (
    ("all", "همه آگهی‌ها"),
    ("consultant", "فقط مشاور"),
    ("personal", "شخصی"),
    ("genuine_personal", "مالک واقعی"),
)

AMENITY_FILTER_FIELDS = (
    ("parking", "پارکینگ"),
    ("warehouse", "انباری"),
    ("elevator", "آسانسور"),
)

AMENITY_FILTERS_BY_CATEGORY: Dict[str, FrozenSet[str]] = {
    "apartment-rent": frozenset({"parking", "warehouse", "elevator"}),
    "apartment-sell": frozenset({"parking", "warehouse", "elevator"}),
    "house-villa-rent": frozenset({"parking", "warehouse"}),
    "house-villa-sell": frozenset({"parking", "warehouse"}),
}


def is_rent_transaction(transaction_type: str) -> bool:
    return "اجاره" in (transaction_type or "")


def parse_optional_int(value: Any) -> Optional[int]:
    if value is None:
        return None
    s = str(value).strip().translate(_EN_DIGITS)
    for ch in ("،", ",", "٬", " ", "\u200c"):
        s = s.replace(ch, "")
    if not s:
        return None
    try:
        return int(float(s))
    except (TypeError, ValueError):
        return None


def format_filter_int(value: Any) -> str:
    if value is None or value == "":
        return ""
    parsed = parse_optional_int(value)
    if parsed is None:
        return str(value).strip()
    return str(parsed)


def parse_amenity_flag(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    s = str(value or "").strip().lower()
    return s in ("1", "true", "yes", "on", "دارد", "بله")


def supported_amenities_for_category(category: str) -> FrozenSet[str]:
    return AMENITY_FILTERS_BY_CATEGORY.get(str(category or "").strip(), frozenset())


def resolve_search_category(category: str, search_filters: Optional[Dict[str, Any]]) -> str:
    """نگاشت سازگاری — residential-sell قدیمی به apartment-sell."""
    cat = str(category or "").strip()
    if cat == "residential-sell":
        return "apartment-sell"
    return cat


def normalize_saved_filters(raw: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """بازیابی فیلتر ذخیره‌شده — سازگار با نسخه‌های قبلی بدون این کلیدها."""
    src = raw or {}
    return {
        "price_min": src.get("price_min"),
        "price_max": src.get("price_max"),
        "deposit_min": src.get("deposit_min"),
        "deposit_max": src.get("deposit_max"),
        "rent_min": src.get("rent_min"),
        "rent_max": src.get("rent_max"),
        "area_min": src.get("area_min"),
        "area_max": src.get("area_max"),
        "year_min": src.get("year_min"),
        "year_max": src.get("year_max"),
        "parking": parse_amenity_flag(src.get("parking")),
        "warehouse": parse_amenity_flag(src.get("warehouse")),
        "elevator": parse_amenity_flag(src.get("elevator")),
        "advertiser_filter": normalize_filter_value(src.get("advertiser_filter") or "all"),
        "search_query": str(src.get("search_query") or "").strip(),
    }


def build_api_filters(ui_filters: Dict[str, Any]) -> Dict[str, Any]:
    """تبدیل مقادیر UI به فیلتر API دیوار."""
    return {
        "price_min": parse_optional_int(ui_filters.get("price_min")),
        "price_max": parse_optional_int(ui_filters.get("price_max")),
        "deposit_min": parse_optional_int(ui_filters.get("deposit_min")),
        "deposit_max": parse_optional_int(ui_filters.get("deposit_max")),
        "rent_min": parse_optional_int(ui_filters.get("rent_min")),
        "rent_max": parse_optional_int(ui_filters.get("rent_max")),
        "area_min": parse_optional_int(ui_filters.get("area_min")),
        "area_max": parse_optional_int(ui_filters.get("area_max")),
        "year_min": parse_optional_int(ui_filters.get("year_min")),
        "year_max": parse_optional_int(ui_filters.get("year_max")),
        "parking": parse_amenity_flag(ui_filters.get("parking")),
        "warehouse": parse_amenity_flag(ui_filters.get("warehouse")),
        "elevator": parse_amenity_flag(ui_filters.get("elevator")),
        "advertiser_filter": normalize_filter_value(ui_filters.get("advertiser_filter") or "all"),
        "search_query": str(ui_filters.get("search_query") or "").strip(),
    }


def has_active_advanced_filters(filters: Dict[str, Any]) -> bool:
    api = build_api_filters(filters)
    for key in (
        "price_min", "price_max", "deposit_min", "deposit_max",
        "rent_min", "rent_max", "area_min", "area_max",
        "year_min", "year_max",
    ):
        if api.get(key) is not None:
            return True
    return any(api.get(k) for k in ("parking", "warehouse", "elevator"))


def normalize_filters_for_job(
    filters: Dict[str, Any],
    *,
    transaction_type: str,
    api_slug: str,
) -> Dict[str, Any]:
    """پاک‌سازی فیلترهای نامرتبط قبل از ارسال به موتور."""
    normalized = normalize_saved_filters(filters)
    rent = is_rent_transaction(transaction_type)

    if rent:
        normalized["price_min"] = None
        normalized["price_max"] = None
    else:
        normalized["deposit_min"] = None
        normalized["deposit_max"] = None
        normalized["rent_min"] = None
        normalized["rent_max"] = None

    supported = supported_amenities_for_category(api_slug)
    for field_key in ("parking", "warehouse", "elevator"):
        if field_key not in supported:
            normalized[field_key] = False

    return normalized
