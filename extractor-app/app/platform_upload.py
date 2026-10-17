"""آپلود خودکار خروجی استخراج به پلتفرم وب."""
from __future__ import annotations

import os
import time
from typing import Any, Callable, Dict, Optional

import requests

from app.brand import DEFAULT_LICENSE_API_URL
from app.extraction_engine import ExtractionEngine
from app.license_client import LicenseClient, _bot_api_headers
from app.places import PlacesManager
from app.retry_utils import is_fatal_error_message, is_transient_http_status


def build_relative_upload_path(
    output_file_path: str,
    settings: Dict[str, Any],
    places: PlacesManager,
) -> str:
    basename = os.path.basename(output_file_path)
    preview = ExtractionEngine.preview_output_structure(settings, places)
    parts = [p.strip() for p in preview.replace(" / ", "/").split("/") if p.strip()]
    if parts and parts[0].lower() == "output":
        parts = parts[1:]
    if not parts:
        return basename
    parts[-1] = basename
    return "/".join(parts)


def upload_extraction_file(
    license_client: LicenseClient,
    output_file_path: str,
    settings: Dict[str, Any],
    places: PlacesManager,
    *,
    on_log: Optional[Callable[[str, str], None]] = None,
) -> Dict[str, Any]:
    def log(msg: str, level: str = "info") -> None:
        if on_log:
            on_log(msg, level)

    if not os.path.isfile(output_file_path):
        return {"success": False, "error": "فایل خروجی یافت نشد."}

    license_info = license_client.get_license_info()
    if not license_info:
        return {"success": False, "error": "لایسنس فعال نیست."}

    license_key = license_info.get("license_key", "").strip()
    hardware = license_client.get_hardware_fingerprint()
    if not license_key:
        return {"success": False, "error": "کلید لایسنس یافت نشد."}

    api_base = (license_info.get("api_base_url") or DEFAULT_LICENSE_API_URL).rstrip("/")
    relative_path = build_relative_upload_path(output_file_path, settings, places)
    log(f"در حال آپلود به پلتفرم… ({relative_path})", "info")

    try:
        with open(output_file_path, "rb") as handle:
            response = requests.post(
                f"{api_base}/api/licenses/import-dataset/",
                data={
                    "license_key": license_key,
                    "hardware_fingerprint": hardware,
                    "relative_path": relative_path,
                },
                files={
                    "file": (os.path.basename(output_file_path), handle),
                },
                headers=_bot_api_headers(),
                timeout=180,
            )
    except requests.exceptions.Timeout:
        return {"success": False, "error": "زمان آپلود به پلتفرم تمام شد."}
    except requests.exceptions.ConnectionError:
        return {"success": False, "error": "اتصال به پلتفرم برقرار نشد."}
    except Exception as exc:
        return {"success": False, "error": str(exc)}

    try:
        data = response.json()
    except Exception:
        return {
            "success": False,
            "error": f"پاسخ نامعتبر از سرور (HTTP {response.status_code})",
        }

    if response.status_code == 200 and data.get("success"):
        msg = data.get("message", "فایل در پلتفرم ثبت شد.")
        log(f"✓ {msg}", "success")
        if data.get("is_update"):
            log(
                f"  {data.get('added_count', 0)} آگهی جدید به مجموعه «{data.get('dataset_name', '')}» اضافه شد.",
                "info",
            )
        return {"success": True, "data": data}

    error = data.get("error", f"آپلود ناموفق (HTTP {response.status_code})")
    log(f"✗ آپلود پلتفرم: {error}", "error")
    return {"success": False, "error": error, "status_code": response.status_code}


def upload_extraction_file_with_retry(
    license_client: LicenseClient,
    output_file_path: str,
    settings: Dict[str, Any],
    places: PlacesManager,
    *,
    on_log: Optional[Callable[[str, str], None]] = None,
    max_attempts: int = 3,
    backoff_seconds: tuple[float, ...] = (2.0, 5.0),
) -> Dict[str, Any]:
    last_result: Dict[str, Any] = {"success": False, "error": "آپلود ناموفق"}
    attempts = max(1, max_attempts)
    for attempt in range(1, attempts + 1):
        result = upload_extraction_file(
            license_client,
            output_file_path,
            settings,
            places,
            on_log=on_log if attempt == 1 else None,
        )
        if result.get("success"):
            return result
        last_result = result
        error = str(result.get("error") or "")
        if is_fatal_error_message(error):
            return result
        status_code = result.get("status_code")
        if not is_transient_http_status(status_code) and "اتصال" not in error and "زمان" not in error:
            return result
        if attempt >= attempts:
            break
        if on_log:
            on_log(f"⚠ تلاش مجدد آپلود ({attempt + 1}/{attempts})…", "warning")
        delay = backoff_seconds[min(attempt - 1, len(backoff_seconds) - 1)]
        time.sleep(delay)
    return last_result
