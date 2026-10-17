"""کلاینت API دسکتاپ — ورود حساب و bind لایسنس."""
from __future__ import annotations

from typing import Any, Dict, List, Optional

import requests

from app.credential_store import (
    clear_session_tokens,
    has_session_tokens,
    load_session_credentials,
    load_session_tokens,
    save_session_tokens,
)


class DesktopAuthError(Exception):
    def __init__(self, message: str, *, code: str = 'ERROR', status: int = 400, fields: Optional[dict] = None):
        self.message = message
        self.code = code
        self.status = status
        self.fields = fields or {}
        super().__init__(message)


class DesktopAuthClient:
    def __init__(self, api_base_url: str) -> None:
        self.api_base_url = api_base_url.rstrip('/')
        self._access_token: Optional[str] = None
        self._refresh_token: Optional[str] = None
        self._load_cached_tokens()

    def _load_cached_tokens(self) -> None:
        cached = load_session_tokens()
        if cached:
            self._access_token = cached.get('access')
            self._refresh_token = cached.get('refresh')

    def has_session(self) -> bool:
        return bool(self._refresh_token or has_session_tokens())

    def get_saved_login(self) -> tuple[str, str]:
        return load_session_credentials()

    def save_login_credentials(self, username: str, password: str) -> None:
        cached = load_session_tokens()
        if not cached or not cached.get("refresh"):
            return
        save_session_tokens(
            access=cached.get("access") or self._access_token or "",
            refresh=cached["refresh"],
            expires_in=int(cached.get("expires_in") or 0),
            username=(username or "").strip(),
            password=password or "",
        )

    def _auth_headers(self) -> Dict[str, str]:
        headers = {'Content-Type': 'application/json', 'Accept': 'application/json'}
        if self._access_token:
            headers['Authorization'] = f'Bearer {self._access_token}'
        return headers

    def _parse_response(self, response: requests.Response) -> Dict[str, Any]:
        try:
            body = response.json() if response.content else {}
        except ValueError:
            body = {}
        if response.status_code >= 400 or not body.get('ok', False):
            msg = body.get('error') or f'HTTP {response.status_code}'
            raise DesktopAuthError(
                msg,
                code=body.get('code', 'ERROR'),
                status=response.status_code,
                fields=body.get('fields') or {},
            )
        return body.get('data') or {}

    def login(self, username: str, password: str) -> Dict[str, Any]:
        response = requests.post(
            f'{self.api_base_url}/api/desktop/v1/auth/login',
            json={'username': username.strip(), 'password': password},
            headers={'Content-Type': 'application/json'},
            timeout=30,
        )
        data = self._parse_response(response)
        user = data.get("user") or {}
        login_id = (
            (user.get("phone") or "").strip()
            or username.strip()
        )
        self._persist_tokens(
            data,
            username=login_id,
            password=password,
        )
        return data

    def refresh(self) -> Dict[str, Any]:
        refresh = self._refresh_token
        if not refresh:
            cached = load_session_tokens()
            refresh = cached.get('refresh') if cached else None
        if not refresh:
            raise DesktopAuthError('session یافت نشد.', code='AUTH_EXPIRED', status=401)
        response = requests.post(
            f'{self.api_base_url}/api/desktop/v1/auth/refresh',
            json={'refresh': refresh},
            headers={'Content-Type': 'application/json'},
            timeout=20,
        )
        data = self._parse_response(response)
        self._persist_tokens(data)
        return data

    def logout(self) -> None:
        refresh = self._refresh_token
        try:
            if self._access_token and refresh:
                requests.post(
                    f'{self.api_base_url}/api/desktop/v1/auth/logout',
                    json={'refresh': refresh},
                    headers=self._auth_headers(),
                    timeout=10,
                )
        except Exception:
            pass
        self._access_token = None
        self._refresh_token = None
        clear_session_tokens()

    def ensure_access_token(self) -> bool:
        if self._access_token:
            return True
        cached = load_session_tokens()
        if cached and cached.get('access'):
            self._access_token = cached['access']
            self._refresh_token = cached.get('refresh')
            return True
        if not self._refresh_token and cached:
            self._refresh_token = cached.get('refresh')
        if self._refresh_token:
            try:
                self.refresh()
                return bool(self._access_token)
            except DesktopAuthError:
                return False
        return False

    def get_eligible(self, hardware_fingerprint: str) -> Dict[str, Any]:
        self.ensure_access_token()
        response = requests.get(
            f'{self.api_base_url}/api/desktop/v1/licenses/eligible',
            params={'hardware_fingerprint': hardware_fingerprint},
            headers=self._auth_headers(),
            timeout=20,
        )
        return self._parse_response(response)

    def bind(
        self,
        hardware_fingerprint: str,
        *,
        license_id: Optional[int] = None,
        device_label: str = 'Windows',
    ) -> Dict[str, Any]:
        self.ensure_access_token()
        payload: Dict[str, Any] = {
            'hardware_fingerprint': hardware_fingerprint,
            'device_label': device_label,
        }
        if license_id is not None:
            payload['license_id'] = license_id
        response = requests.post(
            f'{self.api_base_url}/api/desktop/v1/licenses/bind',
            json=payload,
            headers=self._auth_headers(),
            timeout=30,
        )
        return self._parse_response(response)

    def validate_session(
        self,
        hardware_fingerprint: str,
        *,
        license_key: Optional[str] = None,
    ) -> Dict[str, Any]:
        self.ensure_access_token()
        payload: Dict[str, Any] = {'hardware_fingerprint': hardware_fingerprint}
        if license_key:
            payload['license_key'] = license_key
        response = requests.post(
            f'{self.api_base_url}/api/desktop/v1/licenses/validate-session',
            json=payload,
            headers=self._auth_headers(),
            timeout=20,
        )
        return self._parse_response(response)

    def login_and_bind(
        self,
        username: str,
        password: str,
        hardware_fingerprint: str,
        *,
        license_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        self.login(username, password)
        try:
            return self.bind(hardware_fingerprint, license_id=license_id)
        except DesktopAuthError as exc:
            if exc.code == 'LICENSE_SELECTION_REQUIRED':
                raise
            eligible = self.get_eligible(hardware_fingerprint)
            auto_id = eligible.get('auto_bind_license_id')
            if auto_id and license_id is None:
                return self.bind(hardware_fingerprint, license_id=auto_id)
            raise

    def _persist_tokens(
        self,
        data: Dict[str, Any],
        *,
        username: str | None = None,
        password: str | None = None,
    ) -> None:
        access = data.get('access')
        refresh = data.get('refresh')
        if access:
            self._access_token = access
        if refresh:
            self._refresh_token = refresh
        if access and refresh:
            save_session_tokens(
                access=access,
                refresh=refresh,
                expires_in=int(data.get('expires_in') or 0),
                username=username,
                password=password,
            )
