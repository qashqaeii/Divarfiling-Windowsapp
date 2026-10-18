"""Retry با backoff برای خطاهای موقت شبکه."""
from __future__ import annotations

import time
from typing import Callable, Optional, Set, TypeVar

T = TypeVar("T")

DEFAULT_MAX_ATTEMPTS = 3
DEFAULT_BACKOFF_SECONDS = (2.0, 5.0)


class FatalOperationError(Exception):
    """خطای غیرقابل retry — توفف batch."""

    def __init__(self, message: str, *, category: str = "fatal") -> None:
        super().__init__(message)
        self.category = category


class NonRetryableExtractionError(Exception):
    """خطای قطعی استخراج/خروجی — تکرار کل فرایند شبکه مجاز نیست."""

    def __init__(self, message: str, *, stage: str = "export") -> None:
        super().__init__(message)
        self.stage = stage


FATAL_KEYWORDS = (
    "لایسنس",
    "license",
    "authentication",
    "unauthorized",
    "forbidden",
    "invalid",
    "اعتبار",
    "کلید لایسنس",
    "hardware",
)


def is_fatal_error_message(message: str) -> bool:
    lower = (message or "").lower()
    return any(kw in lower for kw in FATAL_KEYWORDS)


def is_transient_http_status(status_code: Optional[int]) -> bool:
    if status_code is None:
        return True
    return status_code in (408, 429, 500, 502, 503, 504)


def run_with_retry(
    operation: Callable[[], T],
    *,
    max_attempts: int = DEFAULT_MAX_ATTEMPTS,
    backoff_seconds: tuple[float, ...] = DEFAULT_BACKOFF_SECONDS,
    is_retryable: Optional[Callable[[Exception], bool]] = None,
    on_retry: Optional[Callable[[int, Exception], None]] = None,
) -> T:
    last_exc: Optional[Exception] = None
    attempts = max(1, max_attempts)
    for attempt in range(1, attempts + 1):
        try:
            return operation()
        except FatalOperationError:
            raise
        except Exception as exc:
            last_exc = exc
            retryable = True
            if is_retryable is not None:
                retryable = is_retryable(exc)
            if not retryable or attempt >= attempts:
                raise
            if on_retry:
                on_retry(attempt, exc)
            delay = backoff_seconds[min(attempt - 1, len(backoff_seconds) - 1)]
            time.sleep(delay)
    assert last_exc is not None
    raise last_exc
