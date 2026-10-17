"""ذخیره امن توکن‌های session — Windows Credential Manager via keyring."""
from __future__ import annotations

import json
import logging
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

SERVICE_NAME = 'divarfiling-extractor-desktop'
ACCOUNT_NAME = 'desktop-auth-session'


def _keyring():
    try:
        import keyring
        return keyring
    except ImportError:
        return None


def save_session_tokens(
    *,
    access: str,
    refresh: str,
    expires_in: int = 0,
    username: str | None = None,
    password: str | None = None,
) -> bool:
    """ذخیره access/refresh — هرگز در license.json."""
    kr = _keyring()
    if not kr:
        logger.warning('keyring not installed — session tokens not persisted')
        return False
    existing = load_session_tokens() or {}
    payload = json.dumps({
        'access': access,
        'refresh': refresh,
        'expires_in': expires_in,
        'username': username if username is not None else existing.get('username', ''),
        'password': password if password is not None else existing.get('password', ''),
    }, ensure_ascii=False)
    try:
        kr.set_password(SERVICE_NAME, ACCOUNT_NAME, payload)
        return True
    except Exception as exc:
        logger.warning('credential store save failed: %s', exc)
        return False


def load_session_tokens() -> Optional[Dict[str, Any]]:
    kr = _keyring()
    if not kr:
        return None
    try:
        raw = kr.get_password(SERVICE_NAME, ACCOUNT_NAME)
        if not raw:
            return None
        data = json.loads(raw)
        if not data.get('refresh'):
            return None
        return data
    except Exception as exc:
        logger.warning('credential store load failed: %s', exc)
        return None


def clear_session_tokens() -> None:
    kr = _keyring()
    if not kr:
        return
    try:
        kr.delete_password(SERVICE_NAME, ACCOUNT_NAME)
    except Exception:
        pass


def has_session_tokens() -> bool:
    tokens = load_session_tokens()
    return bool(tokens and tokens.get('refresh'))


def load_session_credentials() -> tuple[str, str]:
    tokens = load_session_tokens() or {}
    return (
        str(tokens.get('username') or '').strip(),
        str(tokens.get('password') or ''),
    )
