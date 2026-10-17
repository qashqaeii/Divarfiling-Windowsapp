"""مدل‌های داده batch extraction."""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional


class JobStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    NO_RESULTS = "no_results"
    FAILED = "failed"
    CANCELLED = "cancelled"
    SKIPPED = "skipped"


class UploadStatus(str, Enum):
    NOT_REQUESTED = "not_requested"
    SUCCESS = "success"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class BatchJobSpec:
    transaction_type: str
    subcategory: str
    api_slug: str

    @property
    def label(self) -> str:
        return f"{self.transaction_type} / {self.subcategory}"


@dataclass
class BatchJobResult:
    transaction_type: str
    subcategory: str
    api_slug: str
    extraction_status: JobStatus
    upload_status: UploadStatus
    output_path: Optional[str] = None
    extracted_count: int = 0
    started_at: Optional[str] = None
    finished_at: Optional[str] = None
    error_message: str = ""

    @property
    def is_extraction_ok(self) -> bool:
        return self.extraction_status == JobStatus.SUCCESS

    @property
    def is_retry_candidate(self) -> bool:
        if self.extraction_status in (JobStatus.FAILED, JobStatus.NO_RESULTS):
            return True
        if self.extraction_status == JobStatus.SUCCESS and self.upload_status == UploadStatus.FAILED:
            return True
        return False

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data["extraction_status"] = self.extraction_status.value
        data["upload_status"] = self.upload_status.value
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "BatchJobResult":
        return cls(
            transaction_type=str(data.get("transaction_type") or ""),
            subcategory=str(data.get("subcategory") or ""),
            api_slug=str(data.get("api_slug") or ""),
            extraction_status=JobStatus(str(data.get("extraction_status") or JobStatus.FAILED.value)),
            upload_status=UploadStatus(str(data.get("upload_status") or UploadStatus.SKIPPED.value)),
            output_path=data.get("output_path"),
            extracted_count=int(data.get("extracted_count") or 0),
            started_at=data.get("started_at"),
            finished_at=data.get("finished_at"),
            error_message=str(data.get("error_message") or ""),
        )


@dataclass
class BatchRunSummary:
    batch_id: str
    total_jobs: int
    completed_jobs: int = 0
    results: List[BatchJobResult] = field(default_factory=list)
    started_at: Optional[str] = None
    finished_at: Optional[str] = None
    cancelled: bool = False

    @property
    def success_count(self) -> int:
        return sum(1 for r in self.results if r.extraction_status == JobStatus.SUCCESS)

    @property
    def failed_count(self) -> int:
        return sum(
            1 for r in self.results
            if r.extraction_status in (JobStatus.FAILED, JobStatus.NO_RESULTS)
            or r.upload_status == UploadStatus.FAILED
        )

    @property
    def retry_jobs(self) -> List[BatchJobSpec]:
        specs: List[BatchJobSpec] = []
        for r in self.results:
            if r.is_retry_candidate:
                specs.append(BatchJobSpec(r.transaction_type, r.subcategory, r.api_slug))
        return specs

    def to_dict(self) -> Dict[str, Any]:
        return {
            "batch_id": self.batch_id,
            "total_jobs": self.total_jobs,
            "completed_jobs": self.completed_jobs,
            "started_at": self.started_at,
            "finished_at": self.finished_at,
            "cancelled": self.cancelled,
            "results": [r.to_dict() for r in self.results],
        }


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")
