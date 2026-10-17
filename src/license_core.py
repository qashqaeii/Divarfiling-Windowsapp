"""قوانین مشترک اعتبارسنجی لایسنس در کلاینت‌های دسکتاپ."""
from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional, Tuple

DEFAULT_OFFLINE_GRACE_HOURS = int(os.environ.get('LICENSE_OFFLINE_GRACE_HOURS', '72'))
IN_MEMORY_CACHE_HOURS = int(os.environ.get('LICENSE_CACHE_HOURS', '6'))


def parse_iso(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    try:
        text = str(value).strip()
        if text.endswith('Z'):
            text = text[:-1] + '+00:00'
        dt = datetime.fromisoformat(text)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    except (ValueError, TypeError):
        return None


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def is_expired(expires_at: Optional[str]) -> bool:
    dt = parse_iso(expires_at)
    if not dt:
        return False
    return now_utc() >= dt


def allow_local_dev(license_data: Dict[str, Any]) -> bool:
    if not license_data.get('local_dev'):
        return False
    flag = os.environ.get('LICENSE_ALLOW_LOCAL_DEV', '').strip().lower()
    return flag in ('1', 'true', 'yes')


def offline_grace_active(license_data: Dict[str, Any]) -> bool:
    grace_until = parse_iso(license_data.get('offline_grace_until'))
    if grace_until and now_utc() < grace_until:
        return True
    last_val = parse_iso(license_data.get('last_server_validation_at'))
    if not last_val:
        return False
    return now_utc() < last_val + timedelta(hours=DEFAULT_OFFLINE_GRACE_HOURS)


def in_memory_cache_valid(last_check: Optional[datetime]) -> bool:
    if not last_check:
        return False
    if last_check.tzinfo is None:
        last_check = last_check.replace(tzinfo=timezone.utc)
    return now_utc() - last_check.astimezone(timezone.utc) < timedelta(hours=IN_MEMORY_CACHE_HOURS)


def evaluate_offline_validation(license_data: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
    if is_expired(license_data.get('expires_at')):
        return False, 'لایسنس منقضی شده است.'
    if not license_data.get('last_server_validation_at'):
        return False, 'ابتدا باید یک بار اعتبارسنجی آنلاین موفق انجام شود.'
    if not offline_grace_active(license_data):
        return False, 'اتصال به سرور لازم است — دوره آفلاین به پایان رسیده.'
    return True, None


def merge_server_payload(license_data: Dict[str, Any], server_data: Dict[str, Any]) -> Dict[str, Any]:
    updated = dict(license_data)
    for key in (
        'plan_name', 'plan_id', 'expires_at', 'max_activations', 'status',
        'offline_grace_until', 'offline_grace_hours', 'server_time',
    ):
        if server_data.get(key) is not None:
            updated[key] = server_data.get(key)
    if isinstance(server_data.get('account'), dict):
        updated['account'] = server_data['account']
    if isinstance(server_data.get('allocation'), dict):
        updated['allocation'] = server_data['allocation']
    updated['last_server_validation_at'] = now_utc().isoformat()
    return updated


def merge_activate_payload(license_data: Dict[str, Any], server_data: Dict[str, Any]) -> Dict[str, Any]:
    updated = merge_server_payload(license_data, server_data)
    if server_data.get('activated_at'):
        updated['activated_at'] = server_data['activated_at']
    return updated
