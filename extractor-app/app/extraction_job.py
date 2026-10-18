"""اجرای یک job استخراج — مسیر مشترک single و batch."""
from __future__ import annotations

import copy
import traceback
import uuid
from typing import Any, Callable, Dict, Optional

from app.batch_models import BatchJobResult, JobStatus, UploadStatus, utc_now_iso
from app.extraction_engine import ExtractionEngine
from app.license_client import LicenseClient
from app.platform_upload import upload_extraction_file_with_retry
from app.places import PlacesManager
from app.retry_utils import (
    FatalOperationError,
    NonRetryableExtractionError,
    is_fatal_error_message,
    run_with_retry,
)

LogFn = Callable[[str, str], None]
CancelFn = Callable[[], bool]


class ExtractionJobService:
    """extract → export/merge → upload → BatchJobResult"""

    def __init__(
        self,
        engine: ExtractionEngine,
        license_client: LicenseClient,
        places: PlacesManager,
        *,
        on_log: LogFn,
        is_cancelled: CancelFn,
    ) -> None:
        self.engine = engine
        self.license = license_client
        self.places = places
        self.on_log = on_log
        self.is_cancelled = is_cancelled

    def run(
        self,
        settings: Dict[str, Any],
        *,
        transaction_type: str,
        subcategory: str,
        api_slug: str,
    ) -> BatchJobResult:
        result = BatchJobResult(
            transaction_type=transaction_type,
            subcategory=subcategory,
            api_slug=api_slug,
            extraction_status=JobStatus.RUNNING,
            upload_status=UploadStatus.NOT_REQUESTED,
            started_at=utc_now_iso(),
        )

        if self.is_cancelled():
            result.extraction_status = JobStatus.CANCELLED
            result.upload_status = UploadStatus.SKIPPED
            result.finished_at = utc_now_iso()
            return result

        job_id = uuid.uuid4().hex[:8]
        try:
            output_path = self._run_extraction_with_retry(settings, job_id=job_id)
        except FatalOperationError as exc:
            result.extraction_status = JobStatus.FAILED
            result.error_message = str(exc)
            result.finished_at = utc_now_iso()
            self._log_extraction_failure(job_id, exc, stage="fatal")
            raise
        except Exception as exc:
            if self.is_cancelled():
                result.extraction_status = JobStatus.CANCELLED
                result.upload_status = UploadStatus.SKIPPED
            else:
                result.extraction_status = JobStatus.FAILED
                result.error_message = str(exc)
                self._log_extraction_failure(job_id, exc, stage=getattr(exc, "stage", "extract"))
            result.finished_at = utc_now_iso()
            return result

        if self.is_cancelled():
            result.extraction_status = JobStatus.CANCELLED
            result.upload_status = UploadStatus.SKIPPED
            result.finished_at = utc_now_iso()
            return result

        if not output_path:
            result.extraction_status = JobStatus.NO_RESULTS
            result.error_message = "استخراج بدون فایل خروجی پایان یافت."
            result.finished_at = utc_now_iso()
            return result

        result.output_path = output_path
        result.extraction_status = JobStatus.SUCCESS

        if not settings.get("upload_to_platform"):
            result.upload_status = UploadStatus.NOT_REQUESTED
            result.finished_at = utc_now_iso()
            return result

        if self.is_cancelled():
            result.upload_status = UploadStatus.SKIPPED
            result.finished_at = utc_now_iso()
            return result

        upload_result = self._run_upload_with_retry(output_path, settings)
        if upload_result.get("success"):
            result.upload_status = UploadStatus.SUCCESS
            data = upload_result.get("data") or {}
            result.extracted_count = int(data.get("added_count") or 0)
        else:
            result.upload_status = UploadStatus.FAILED
            err = str(upload_result.get("error") or "آپلود ناموفق")
            result.error_message = err

        result.finished_at = utc_now_iso()
        return result

    def _log_extraction_failure(self, job_id: str, exc: Exception, *, stage: str) -> None:
        self.on_log(
            f"✗ [job {job_id}] شکست استخراج ({stage}): {type(exc).__name__}: {exc}",
            "error",
        )
        self.engine.storage.append_log(
            f"EXTRACT FAIL job={job_id} stage={stage} "
            f"err={type(exc).__name__}: {exc}\n{traceback.format_exc()}"
        )

    def _run_extraction_with_retry(
        self, settings: Dict[str, Any], *, job_id: str
    ) -> Optional[str]:
        def _attempt() -> Optional[str]:
            if self.is_cancelled():
                return None
            return self.engine.run(settings)

        def _on_retry(attempt: int, exc: Exception) -> None:
            self.on_log(
                f"⚠ [job {job_id} تلاش {attempt + 1}/۳] خطای موقت شبکه/استخراج: {exc}",
                "warning",
            )
            self.engine.storage.append_log(
                f"RETRY job={job_id} attempt={attempt + 1} err={type(exc).__name__}: {exc}"
            )

        def _retryable(exc: Exception) -> bool:
            if isinstance(exc, (FatalOperationError, NonRetryableExtractionError)):
                return False
            return not is_fatal_error_message(str(exc))

        self.on_log(f"[job {job_id}] شروع استخراج (حداکثر ۳ تلاش برای خطای موقت)", "info")
        return run_with_retry(
            _attempt,
            on_retry=_on_retry,
            is_retryable=_retryable,
        )

    def _run_upload_with_retry(
        self,
        output_path: str,
        settings: Dict[str, Any],
    ) -> Dict[str, Any]:
        if self.is_cancelled():
            return {"success": False, "error": "لغو شد"}
        result = upload_extraction_file_with_retry(
            self.license,
            output_path,
            settings,
            self.places,
            on_log=self.on_log,
            max_attempts=3,
        )
        err = str(result.get("error") or "")
        if not result.get("success") and is_fatal_error_message(err):
            raise FatalOperationError(err, category="license")
        return result
