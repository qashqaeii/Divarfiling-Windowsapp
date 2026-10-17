"""کلاینت لایسنس — نسخه اپ استخراج (config جدا)."""
from __future__ import annotations

import hashlib
import json
import os
import platform
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

import requests

from app.brand import DEFAULT_LICENSE_API_URL, LICENSE_BOT_API_KEY
from app.paths import get_config_dir

_src = Path(__file__).resolve().parents[2] / 'src'
if str(_src) not in sys.path:
    sys.path.insert(0, str(_src))
from license_core import (  # noqa: E402
    allow_local_dev,
    evaluate_offline_validation,
    in_memory_cache_valid,
    is_expired,
    merge_activate_payload,
    merge_server_payload,
    now_utc,
)


def _bot_api_headers() -> Dict[str, str]:
    key = os.environ.get("LICENSE_BOT_API_KEY", "").strip() or LICENSE_BOT_API_KEY
    return {"X-Bot-Api-Key": key} if key else {}


class LicenseClient:
    def __init__(self, api_base_url: str = DEFAULT_LICENSE_API_URL) -> None:
        self.api_base_url = api_base_url.rstrip("/")
        self.license_file_path = os.path.join(get_config_dir(), "license.json")
        self._cached_license: Optional[Dict[str, Any]] = None
        self._last_validation: Optional[datetime] = None

    def get_hardware_fingerprint(self) -> str:
        try:
            system_info = [
                platform.system(),
                platform.release(),
                platform.version(),
            ]
            try:
                system_info.append(platform.node())
            except Exception:
                pass
            if platform.system() == "Windows":
                for cmd in (
                    ["wmic", "cpu", "get", "ProcessorId"],
                    ["wmic", "diskdrive", "get", "SerialNumber"],
                    ["wmic", "csproduct", "get", "UUID"],
                ):
                    try:
                        result = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
                        if result.returncode == 0:
                            lines = [ln.strip() for ln in result.stdout.strip().split("\n") if ln.strip()]
                            if len(lines) > 1:
                                system_info.append(lines[1])
                    except Exception:
                        pass
            combined = "|".join(system_info)
            return hashlib.sha256(combined.encode("utf-8")).hexdigest()
        except Exception:
            fallback = f"{platform.system()}-{platform.node()}-{platform.machine()}"
            return hashlib.sha256(fallback.encode("utf-8")).hexdigest()

    def activate_license(self, license_key: str) -> Dict[str, Any]:
        hardware_fingerprint = self.get_hardware_fingerprint()
        try:
            response = requests.post(
                f"{self.api_base_url}/api/licenses/activate/",
                json={
                    "license_key": license_key.strip().upper(),
                    "hardware_fingerprint": hardware_fingerprint,
                },
                headers=_bot_api_headers(),
                timeout=30,
            )
            if response.status_code == 200:
                data = response.json()
                if data.get("success"):
                    license_data = {
                        "license_key": license_key.strip().upper(),
                        "hardware_fingerprint": hardware_fingerprint,
                        "activated_at": data.get("activated_at", now_utc().isoformat()),
                        "api_base_url": self.api_base_url,
                    }
                    license_data = merge_activate_payload(license_data, data)
                    self._save_license(license_data)
                    self._cached_license = license_data
                    self._last_validation = datetime.now()
                    return {
                        "success": True,
                        "message": data.get("message", "لایسنس فعال شد."),
                        "data": license_data,
                        "plan_name": data.get("plan_name"),
                    }
                return {"success": False, "error": data.get("error", "خطای فعال‌سازی")}
            error_data = response.json() if response.content else {}
            return {"success": False, "error": error_data.get("error", f"HTTP {response.status_code}")}
        except requests.exceptions.Timeout:
            return {"success": False, "error": "زمان اتصال به سرور تمام شد."}
        except requests.exceptions.ConnectionError:
            return {"success": False, "error": "امکان اتصال به سرور وجود ندارد."}
        except Exception as exc:
            return {"success": False, "error": str(exc)}

    def validate_license(
        self,
        force_check: bool = False,
        *,
        keep_account_fields: bool = False,
    ) -> Dict[str, Any]:
        license_data = self._load_license()
        if not license_data:
            return {"valid": False, "error": "لایسنس یافت نشد."}

        license_key = license_data.get("license_key")
        hardware_fingerprint = self.get_hardware_fingerprint()
        if license_data.get("hardware_fingerprint") != hardware_fingerprint:
            return {"valid": False, "error": "لایسنس برای سیستم دیگری فعال شده است."}

        if is_expired(license_data.get("expires_at")):
            return {"valid": False, "error": "لایسنس منقضی شده است."}

        if allow_local_dev(license_data):
            return {
                "valid": True,
                "offline": True,
                "local_dev": True,
                "license_key": license_key,
            }

        if not force_check and in_memory_cache_valid(self._last_validation):
            ok, err = evaluate_offline_validation(license_data)
            if ok:
                return {
                    "valid": True,
                    "cached": True,
                    "license_key": license_key,
                    "plan_name": license_data.get("plan_name"),
                    "expires_at": license_data.get("expires_at"),
                }
            if err:
                return {"valid": False, "error": err}

        saved_account = license_data.get("account") if keep_account_fields else None
        saved_allocation = license_data.get("allocation") if keep_account_fields else None

        try:
            response = requests.post(
                f"{self.api_base_url}/api/licenses/validate/",
                json={"license_key": license_key, "hardware_fingerprint": hardware_fingerprint},
                headers=_bot_api_headers(),
                timeout=10,
            )
            if response.status_code == 200:
                data = response.json()
                self._last_validation = datetime.now()
                if data.get("valid"):
                    license_data = merge_server_payload(license_data, data)
                    if keep_account_fields:
                        if saved_account is not None:
                            license_data["account"] = saved_account
                        if saved_allocation is not None:
                            license_data["allocation"] = saved_allocation
                    self._save_license(license_data)
                    self._cached_license = license_data
                    return {
                        "valid": True,
                        "license_key": license_key,
                        "message": "لایسنس معتبر است",
                        "plan_name": data.get("plan_name"),
                        "expires_at": data.get("expires_at"),
                        "max_activations": data.get("max_activations"),
                    }
                return {
                    "valid": False,
                    "error": data.get("error", "لایسنس نامعتبر"),
                }

            ok, err = evaluate_offline_validation(license_data)
            if ok:
                return {
                    "valid": True,
                    "offline": True,
                    "license_key": license_key,
                    "message": "لایسنس معتبر است (آفلاین — سرور در دسترس نیست)",
                }
            return {"valid": False, "error": err or "اعتبارسنجی با سرور ناموفق بود."}

        except (requests.exceptions.Timeout, requests.exceptions.ConnectionError):
            ok, err = evaluate_offline_validation(license_data)
            if ok:
                return {
                    "valid": True,
                    "offline": True,
                    "license_key": license_key,
                    "message": "لایسنس معتبر است (آفلاین)",
                }
            return {"valid": False, "error": err or "اتصال به سرور برقرار نیست."}
        except Exception as exc:
            return {"valid": False, "error": str(exc)}

    def report_client_event(
        self,
        event_type: str,
        *,
        app_version: str = '',
        platform: str = 'windows',
    ) -> Dict[str, Any]:
        license_data = self._load_license()
        if not license_data:
            return {"success": False, "error": "لایسنس یافت نشد."}

        reported_key = f"{event_type}_reported"
        if license_data.get(reported_key):
            return {"success": True, "skipped": True, "message": "رویداد قبلاً گزارش شده است."}

        license_key = license_data.get("license_key")
        hardware_fingerprint = self.get_hardware_fingerprint()
        if not license_key:
            return {"success": False, "error": "کلید لایسنس یافت نشد."}

        try:
            response = requests.post(
                f"{self.api_base_url}/api/licenses/client-event/",
                json={
                    "license_key": license_key,
                    "hardware_fingerprint": hardware_fingerprint,
                    "event_type": event_type,
                    "app_version": app_version,
                    "platform": platform,
                },
                headers=_bot_api_headers(),
                timeout=10,
            )
            if response.status_code == 200:
                data = response.json()
                if data.get("success"):
                    license_data[reported_key] = True
                    self._save_license(license_data)
                    self._cached_license = license_data
                return data
            error_data = response.json() if response.content else {}
            return {
                "success": False,
                "error": error_data.get("error", f"HTTP {response.status_code}"),
            }
        except (requests.exceptions.Timeout, requests.exceptions.ConnectionError):
            return {"success": False, "error": "اتصال به سرور برقرار نیست."}
        except Exception as exc:
            return {"success": False, "error": str(exc)}

    def deactivate_license(self) -> Dict[str, Any]:
        license_data = self._load_license()
        if not license_data:
            return {"success": False, "error": "لایسنس یافت نشد"}
        try:
            response = requests.post(
                f"{self.api_base_url}/api/licenses/deactivate/",
                json={
                    "license_key": license_data.get("license_key"),
                    "hardware_fingerprint": self.get_hardware_fingerprint(),
                },
                headers=_bot_api_headers(),
                timeout=10,
            )
            if response.status_code != 200:
                error_data = response.json() if response.content else {}
                return {
                    "success": False,
                    "error": error_data.get("error", f"HTTP {response.status_code}"),
                }
        except Exception:
            return {"success": False, "error": "غیرفعال‌سازی با سرور ناموفق بود."}
        self._delete_license()
        return {"success": True, "message": "لایسنس غیرفعال شد"}

    def release_local_license(self) -> None:
        """حذف license.json محلی — بدون تماس با سرور."""
        self._delete_license()

    def deactivate_or_clear_local(self) -> Dict[str, Any]:
        """غیرفعال‌سازی روی سرور؛ در صورت خطا حداقل فایل محلی پاک می‌شود."""
        result = self.deactivate_license()
        if not result.get("success") and self.get_license_info():
            self.release_local_license()
            return {
                "success": True,
                "message": "لایسنس محلی پاک شد (اتصال به سرور برقرار نبود).",
                "offline": True,
            }
        return result

    def _save_license(self, license_data: Dict[str, Any]) -> None:
        os.makedirs(os.path.dirname(self.license_file_path), exist_ok=True)
        with open(self.license_file_path, "w", encoding="utf-8") as f:
            json.dump(license_data, f, ensure_ascii=False, indent=2)

    def _load_license(self) -> Optional[Dict[str, Any]]:
        if self._cached_license:
            return self._cached_license
        if not os.path.exists(self.license_file_path):
            return None
        try:
            with open(self.license_file_path, "r", encoding="utf-8") as f:
                self._cached_license = json.load(f)
                return self._cached_license
        except Exception:
            return None

    def _delete_license(self) -> None:
        if os.path.exists(self.license_file_path):
            os.remove(self.license_file_path)
        self._cached_license = None
        self._last_validation = None

    def get_license_info(self) -> Optional[Dict[str, Any]]:
        return self._load_license()

    def apply_bind_payload(self, payload: Dict[str, Any], license_key: str) -> None:
        """ذخیره license.json پس از bind حساب — بدون توکن."""
        hardware_fingerprint = self.get_hardware_fingerprint()
        license_data: Dict[str, Any] = {
            "license_key": license_key.strip().upper(),
            "hardware_fingerprint": hardware_fingerprint,
            "activated_at": payload.get("activated_at", now_utc().isoformat()),
            "api_base_url": self.api_base_url,
        }
        license_data = merge_activate_payload(license_data, payload)
        self._save_license(license_data)
        self._cached_license = license_data
        self._last_validation = datetime.now()

