"""اجرای ترتیبی batch extraction."""
from __future__ import annotations

import uuid
from typing import Any, Callable, Dict, List, Optional

from app.batch_models import BatchJobResult, BatchJobSpec, BatchRunSummary, JobStatus, UploadStatus, utc_now_iso
from app.category_jobs import build_job_settings, iter_subcategory_jobs
from app.extraction_job import ExtractionJobService
from app.retry_utils import FatalOperationError
from app.storage import ExtractorStorage

LogFn = Callable[[str, str], None]
ProgressFn = Callable[[int, int, float, str], None]
JobCompleteFn = Callable[[int, BatchJobResult], None]
CancelFn = Callable[[], bool]


class BatchExtractionRunner:
    def __init__(
        self,
        job_service: ExtractionJobService,
        storage: ExtractorStorage,
        *,
        on_log: LogFn,
        on_progress: ProgressFn,
        is_cancelled: CancelFn,
        on_job_complete: Optional[JobCompleteFn] = None,
    ) -> None:
        self.job_service = job_service
        self.storage = storage
        self.on_log = on_log
        self.on_progress = on_progress
        self.is_cancelled = is_cancelled
        self.on_job_complete = on_job_complete

    def build_jobs(
        self,
        *,
        selected_transactions: Optional[List[str]] = None,
        selected_job_keys: Optional[List[tuple[str, str]]] = None,
    ) -> List[Dict[str, str]]:
        return iter_subcategory_jobs(
            selected_transactions=selected_transactions,
            selected_job_keys=selected_job_keys,
        )

    def run(
        self,
        base_settings: Dict[str, Any],
        jobs: List[Dict[str, str]],
        *,
        batch_id: Optional[str] = None,
    ) -> BatchRunSummary:
        run_id = batch_id or uuid.uuid4().hex[:12]
        summary = BatchRunSummary(
            batch_id=run_id,
            total_jobs=len(jobs),
            started_at=utc_now_iso(),
        )
        self.storage.create_batch_run(run_id, base_settings, len(jobs))

        for index, job in enumerate(jobs):
            if self.is_cancelled():
                summary.cancelled = True
                self.on_log("✗ batch لغو شد — jobهای باقی‌مانده رد می‌شوند.", "warning")
                break

            label = f"{job['transaction_type']} / {job['subcategory']}"
            self.on_log(f"▶ [{index + 1}/{len(jobs)}] {label}", "info")
            self.on_progress(index, len(jobs), 0.0, label)

            settings = build_job_settings(base_settings, job)
            job_row_id = self.storage.create_batch_job(
                run_id,
                job_index=index,
                transaction_type=job["transaction_type"],
                subcategory=job["subcategory"],
                api_slug=job["api_slug"],
            )

            try:
                result = self.job_service.run(
                    settings,
                    transaction_type=job["transaction_type"],
                    subcategory=job["subcategory"],
                    api_slug=job["api_slug"],
                )
            except FatalOperationError as exc:
                result = BatchJobResult(
                    transaction_type=job["transaction_type"],
                    subcategory=job["subcategory"],
                    api_slug=job["api_slug"],
                    extraction_status=JobStatus.FAILED,
                    upload_status=UploadStatus.SKIPPED,
                    error_message=str(exc),
                    finished_at=utc_now_iso(),
                )
                summary.results.append(result)
                summary.completed_jobs = index + 1
                self.storage.save_batch_job_result(job_row_id, result)
                self.storage.update_batch_run(run_id, summary.completed_jobs, cancelled=True)
                if self.on_job_complete:
                    self.on_job_complete(index, result)
                self.on_log(f"✗ خطای بحرانی — batch متوقف شد: {exc}", "error")
                summary.cancelled = True
                break

            summary.results.append(result)
            summary.completed_jobs = index + 1
            self.storage.save_batch_job_result(job_row_id, result)
            self.storage.update_batch_run(run_id, summary.completed_jobs, cancelled=summary.cancelled)
            if self.on_job_complete:
                self.on_job_complete(index, result)

            status_icon = "✓" if result.extraction_status == JobStatus.SUCCESS else "⚠"
            upload_note = ""
            if result.upload_status == UploadStatus.SUCCESS:
                upload_note = " — آپلود موفق"
            elif result.upload_status == UploadStatus.FAILED:
                upload_note = " — آپلود ناموفق"
            self.on_log(
                f"{status_icon} [{index + 1}/{len(jobs)}] {label}{upload_note}",
                "success" if result.extraction_status == JobStatus.SUCCESS else "warning",
            )
            self.on_progress(index + 1, len(jobs), 1.0, label)

        summary.finished_at = utc_now_iso()
        self.storage.finish_batch_run(run_id, summary.cancelled)
        return summary

    def run_specs(
        self,
        base_settings: Dict[str, Any],
        specs: List[BatchJobSpec],
        *,
        batch_id: Optional[str] = None,
    ) -> BatchRunSummary:
        jobs = [
            {
                "transaction_type": s.transaction_type,
                "subcategory": s.subcategory,
                "api_slug": s.api_slug,
            }
            for s in specs
        ]
        return self.run(base_settings, jobs, batch_id=batch_id)
