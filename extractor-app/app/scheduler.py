"""زمان‌بندی خودکار استخراج — اجرای دوره‌ای با شمارش معکوس."""
from __future__ import annotations

import time
from typing import Any, Callable, Dict, Optional

from app.formatters import format_duration_fa, format_timestamp_fa

OnRunFn = Callable[[], None]
OnStatusFn = Callable[[str], None]


class ExtractionScheduler:
    def __init__(self, master, on_run: OnRunFn, on_status: OnStatusFn) -> None:
        self._master = master
        self._on_run = on_run
        self._on_status = on_status
        self._running = False
        self._after_id: Optional[str] = None
        self._pulse_id: Optional[str] = None
        self._interval_hours = 6.0
        self._next_run_at: Optional[float] = None
        self._last_run_at: Optional[float] = None
        self._run_count = 0

    @property
    def is_running(self) -> bool:
        return self._running

    @property
    def next_run_at(self) -> Optional[float]:
        return self._next_run_at

    @property
    def last_run_at(self) -> Optional[float]:
        return self._last_run_at

    @property
    def run_count(self) -> int:
        return self._run_count

    @property
    def interval_hours(self) -> float:
        return self._interval_hours

    @property
    def remaining_seconds(self) -> Optional[int]:
        if not self._running or not self._next_run_at:
            return None
        return max(0, int(self._next_run_at - time.time()))

    def start(self, interval_hours: float) -> None:
        self._interval_hours = max(0.5, float(interval_hours or 1))
        self._running = True
        self._next_run_at = None
        self._start_pulse()
        self._on_status(self._status_text())
        self._on_run()

    def resume(self, interval_hours: float) -> None:
        """ادامهٔ زمان‌بندی بدون اجرای فوری (مثلاً بعد از باز کردن برنامه)."""
        self._interval_hours = max(0.5, float(interval_hours or 1))
        self._running = True
        self._start_pulse()
        self.on_extraction_finished()

    def stop(self) -> None:
        self._running = False
        self._cancel_after()
        self._cancel_pulse()
        self._next_run_at = None
        self._on_status("متوقف")

    def on_extraction_finished(self) -> None:
        if not self._running:
            return
        self._last_run_at = time.time()
        self._run_count += 1
        delay_ms = int(self._interval_hours * 3600 * 1000)
        self._next_run_at = time.time() + self._interval_hours * 3600
        self._cancel_after()
        self._after_id = self._master.after(delay_ms, self._tick)
        self._on_status(self._status_text())

    def mark_run_started(self) -> None:
        self._next_run_at = None
        self._on_status(self._status_text())

    def _tick(self) -> None:
        self._after_id = None
        if self._running:
            self._next_run_at = None
            self._on_status(self._status_text())
            self._on_run()

    def _start_pulse(self) -> None:
        self._cancel_pulse()
        self._pulse()

    def _pulse(self) -> None:
        self._pulse_id = None
        if not self._running:
            return
        self._on_status(self._status_text())
        self._pulse_id = self._master.after(1_000, self._pulse)

    def _cancel_after(self) -> None:
        if self._after_id:
            try:
                self._master.after_cancel(self._after_id)
            except Exception:
                pass
            self._after_id = None

    def _cancel_pulse(self) -> None:
        if self._pulse_id:
            try:
                self._master.after_cancel(self._pulse_id)
            except Exception:
                pass
            self._pulse_id = None

    def _status_text(self) -> str:
        if not self._running:
            return "متوقف"
        if self._next_run_at:
            rem = self.remaining_seconds
            nxt = format_timestamp_fa(self._next_run_at)
            if rem is not None:
                return f"فعال — بعدی {nxt} ({_fmt_remaining(rem)})"
            return f"فعال — اجرای بعدی: {nxt}"
        return "فعال — در حال اجرا"


def _fmt_remaining(seconds: int) -> str:
    return format_duration_fa(seconds, style="words")


def parse_interval_hours(value: str, default: float = 6.0) -> float:
    try:
        return max(0.5, min(float(str(value or "").replace("،", ".").strip()), 168.0))
    except (TypeError, ValueError):
        return default


# گزینه‌های تکرار زمان‌بندی — (ساعت، برچسب فارسی)
SCHEDULER_INTERVAL_PRESETS: list[tuple[float, str]] = [
    (0.5, "هر ۳۰ دقیقه"),
    (1.0, "هر ۱ ساعت"),
    (2.0, "هر ۲ ساعت"),
    (3.0, "هر ۳ ساعت"),
    (6.0, "هر ۶ ساعت"),
    (12.0, "هر ۱۲ ساعت"),
    (24.0, "هر ۲۴ ساعت (روزانه)"),
    (48.0, "هر ۴۸ ساعت (دو روزه)"),
    (168.0, "هر هفته"),
]

# حداقل بازه برای استخراج گروهی زمان‌بندی‌شده
SCHEDULER_BATCH_MIN_HOURS = 3.0


def scheduler_interval_presets(*, mode: str = "single") -> list[tuple[float, str]]:
    if mode == "batch":
        return [(h, label) for h, label in SCHEDULER_INTERVAL_PRESETS if h >= SCHEDULER_BATCH_MIN_HOURS]
    return list(SCHEDULER_INTERVAL_PRESETS)


def scheduler_interval_labels(*, mode: str = "single") -> list[str]:
    return [label for _, label in scheduler_interval_presets(mode=mode)]


def interval_label_to_hours(label: str, default: float = 6.0) -> float:
    for hours, text in SCHEDULER_INTERVAL_PRESETS:
        if text == label:
            return hours
    return parse_interval_hours(label, default=default)


def hours_to_interval_label(
    hours: float,
    default_label: str = "هر ۶ ساعت",
    *,
    mode: str = "single",
) -> str:
    try:
        value = float(hours)
    except (TypeError, ValueError):
        return default_label
    presets = scheduler_interval_presets(mode=mode)
    if not presets:
        presets = list(SCHEDULER_INTERVAL_PRESETS)
    best_label = presets[0][1]
    best_diff = float("inf")
    for preset_hours, label in presets:
        diff = abs(preset_hours - value)
        if diff < best_diff:
            best_diff = diff
            best_label = label
    return best_label


def normalize_interval_hours(hours: float, *, mode: str = "single") -> float:
    return interval_label_to_hours(hours_to_interval_label(hours, mode=mode))


def clamp_interval_for_mode(hours: float, *, mode: str = "single") -> float:
    value = normalize_interval_hours(hours, mode=mode)
    if mode == "batch" and value < SCHEDULER_BATCH_MIN_HOURS:
        return SCHEDULER_BATCH_MIN_HOURS
    return value


def default_scheduler_config() -> Dict[str, Any]:
    return {
        "enabled": False,
        "mode": "single",
        "interval_hours": 6,
        "transaction_type": "فروش مسکونی",
        "subcategory": "",
        "province": "",
        "city": "",
        "district": "",
        "max_items": 100,
        "output_format": "excel",
        "download_images": False,
        "upload_to_platform": True,
        "advertiser_filter": "all",
        "search_query": "",
        "run_immediately": True,
        "batch_preset": "all",
        "batch_job_keys": [],
    }
