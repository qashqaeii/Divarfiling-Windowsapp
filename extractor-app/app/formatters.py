"""قالب‌بندی متن فارسی برای UI."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

import jdatetime

_FA_DIGITS = str.maketrans("0123456789", "۰۱۲۳۴۵۶۷۸۹")


def fa_digits(value) -> str:
    return str(value).translate(_FA_DIGITS)


def _parse_iso_datetime(iso_value: str) -> datetime:
    raw = iso_value.replace("Z", "+00:00")
    return datetime.fromisoformat(raw)


def _to_jalali_datetime(dt: datetime) -> jdatetime.datetime:
    if dt.tzinfo is not None:
        dt = dt.astimezone()
    return jdatetime.datetime.fromgregorian(
        year=dt.year,
        month=dt.month,
        day=dt.day,
        hour=dt.hour,
        minute=dt.minute,
        second=dt.second,
    )


def format_timestamp_fa(ts: float) -> str:
    """تبدیل timestamp محلی به تاریخ و ساعت شمسی با ارقام فارسی."""
    try:
        dt = datetime.fromtimestamp(ts)
        jdt = _to_jalali_datetime(dt)
        return fa_digits(jdt.strftime("%Y/%m/%d — %H:%M"))
    except (TypeError, ValueError, OSError, OverflowError):
        return fa_digits(str(ts))


def format_duration_fa(seconds: Optional[int], *, style: str = "words") -> str:
    """مدت‌زمان حرفه‌ای — بدون مخفف س/د/ث.

    style:
      - words: «۲ ساعت و ۱۵ دقیقه»، «۵۵ دقیقه و ۳۰ ثانیه»، «۳ ثانیه»
      - clock: «۰۲:۱۵:۳۰»
    """
    try:
        total = max(0, int(seconds or 0))
    except (TypeError, ValueError):
        return "—"

    h, rem = divmod(total, 3600)
    m, s = divmod(rem, 60)

    if style == "clock":
        return fa_digits(f"{h:02d}:{m:02d}:{s:02d}")

    parts: list[str] = []
    if h:
        parts.append(f"{fa_digits(h)} ساعت")
        if m:
            parts.append(f"{fa_digits(m)} دقیقه")
    elif m:
        parts.append(f"{fa_digits(m)} دقیقه")
        if s:
            parts.append(f"{fa_digits(s)} ثانیه")
    else:
        parts.append(f"{fa_digits(s)} ثانیه")

    if len(parts) == 1:
        return parts[0]
    return f"{parts[0]} و {parts[1]}"


def format_datetime_fa(iso_value: Optional[str]) -> str:
    """تاریخ و ساعت شمسی با ارقام فارسی."""
    if not iso_value:
        return "—"
    try:
        dt = _parse_iso_datetime(iso_value)
        jdt = _to_jalali_datetime(dt)
        return fa_digits(jdt.strftime("%Y/%m/%d — %H:%M"))
    except (TypeError, ValueError):
        return fa_digits(str(iso_value))


def format_date_fa(iso_value: Optional[str]) -> str:
    """تاریخ شمسی (بدون ساعت)."""
    if not iso_value:
        return "—"
    try:
        dt = _parse_iso_datetime(iso_value)
        jdt = _to_jalali_datetime(dt)
        return fa_digits(jdt.strftime("%Y/%m/%d"))
    except (TypeError, ValueError):
        return fa_digits(str(iso_value))


def format_expiry_fa(iso_value: Optional[str]) -> str:
    if not iso_value:
        return "مادام‌العمر (بدون انقضا)"
    text = format_datetime_fa(iso_value)
    try:
        dt = _parse_iso_datetime(iso_value)
        now = datetime.now(dt.tzinfo) if dt.tzinfo else datetime.now(timezone.utc).astimezone()
        if dt < now:
            return f"منقضی شده — {text}"
        return text
    except (TypeError, ValueError):
        return text


def format_price_toman(value: Optional[int]) -> str:
    """قیمت/مبلغ با جداکننده هزارگان و ارقام فارسی."""
    if value is None:
        return "—"
    try:
        amount = int(value)
    except (TypeError, ValueError):
        return "—"
    if amount <= 0:
        return "—"
    if amount >= 1_000_000_000:
        billions = amount / 1_000_000_000
        if billions == int(billions):
            return f"{fa_digits(int(billions))} میلیارد تومان"
        return f"{fa_digits(f'{billions:.1f}')} میلیارد تومان"
    if amount >= 1_000_000:
        millions = amount / 1_000_000
        if millions == int(millions):
            return f"{fa_digits(int(millions))} میلیون تومان"
        return f"{fa_digits(f'{millions:.1f}')} میلیون تومان"
    return f"{fa_digits(f'{amount:,}')} تومان"
