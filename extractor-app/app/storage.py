"""ذخیره‌سازی محلی اپ استخراج — تنظیمات، resume، batch، لاگ."""
from __future__ import annotations

import json
import os
import sqlite3
import threading
from datetime import datetime
from typing import Any, Dict, List, Optional

from app.batch_models import BatchJobResult
from app.paths import get_app_data_dir


class ExtractorStorage:
    _lock = threading.Lock()

    def __init__(self) -> None:
        self.data_dir = get_app_data_dir()
        self.settings_path = os.path.join(self.data_dir, "settings.json")
        self.db_path = os.path.join(self.data_dir, "extractor.db")
        self.log_path = os.path.join(self.data_dir, "extraction.log")
        self._init_db()

    def _conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        with self._lock:
            conn = self._conn()
            try:
                conn.executescript(
                    """
                    CREATE TABLE IF NOT EXISTS scrape_jobs (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        job_key TEXT UNIQUE,
                        state TEXT NOT NULL,
                        output_path TEXT,
                        updated_at TEXT
                    );
                    CREATE TABLE IF NOT EXISTS batch_runs (
                        id TEXT PRIMARY KEY,
                        base_settings TEXT NOT NULL,
                        total_jobs INTEGER NOT NULL,
                        completed_jobs INTEGER NOT NULL DEFAULT 0,
                        cancelled INTEGER NOT NULL DEFAULT 0,
                        started_at TEXT,
                        finished_at TEXT
                    );
                    CREATE TABLE IF NOT EXISTS batch_job_results (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        batch_id TEXT NOT NULL,
                        job_index INTEGER NOT NULL,
                        transaction_type TEXT NOT NULL,
                        subcategory TEXT NOT NULL,
                        api_slug TEXT NOT NULL,
                        result_json TEXT NOT NULL,
                        updated_at TEXT,
                        FOREIGN KEY (batch_id) REFERENCES batch_runs(id)
                    );
                    CREATE INDEX IF NOT EXISTS idx_batch_job_results_batch
                        ON batch_job_results(batch_id);
                    CREATE TABLE IF NOT EXISTS scheduler_runs (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        started_at TEXT NOT NULL,
                        finished_at TEXT,
                        status TEXT NOT NULL,
                        province TEXT,
                        city TEXT,
                        district TEXT,
                        transaction_type TEXT,
                        subcategory TEXT,
                        search_query TEXT,
                        max_items INTEGER DEFAULT 0,
                        output_format TEXT,
                        output_path TEXT,
                        total_posts INTEGER DEFAULT 0,
                        ok_count INTEGER DEFAULT 0,
                        duration_seconds INTEGER DEFAULT 0,
                        error_message TEXT,
                        advertiser_filter TEXT
                    );
                    CREATE INDEX IF NOT EXISTS idx_scheduler_runs_finished
                        ON scheduler_runs(finished_at DESC);
                    """
                )
                # مهاجرت ستون‌های حالت گروهی زمان‌بندی
                cols = {
                    str(row[1])
                    for row in conn.execute("PRAGMA table_info(scheduler_runs)").fetchall()
                }
                migrations = (
                    ("mode", "TEXT DEFAULT 'single'"),
                    ("jobs_total", "INTEGER DEFAULT 0"),
                    ("jobs_success", "INTEGER DEFAULT 0"),
                    ("jobs_failed", "INTEGER DEFAULT 0"),
                )
                for name, decl in migrations:
                    if name not in cols:
                        conn.execute(f"ALTER TABLE scheduler_runs ADD COLUMN {name} {decl}")
                conn.commit()
            finally:
                conn.close()

    def load_settings(self) -> Dict[str, Any]:
        if not os.path.isfile(self.settings_path):
            return {}
        try:
            with open(self.settings_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}

    def save_settings(self, settings: Dict[str, Any]) -> None:
        with self._lock:
            with open(self.settings_path, "w", encoding="utf-8") as f:
                json.dump(settings, f, ensure_ascii=False, indent=2)

    def save_scrape_state(self, job_key: str, state: Dict[str, Any]) -> None:
        payload = json.dumps(state, ensure_ascii=False)
        now = datetime.now().isoformat(timespec="seconds")
        with self._lock:
            conn = self._conn()
            try:
                conn.execute(
                    """
                    INSERT INTO scrape_jobs (job_key, state, output_path, updated_at)
                    VALUES (?, ?, ?, ?)
                    ON CONFLICT(job_key) DO UPDATE SET
                        state=excluded.state,
                        output_path=excluded.output_path,
                        updated_at=excluded.updated_at
                    """,
                    (job_key, payload, state.get("output_path", ""), now),
                )
                conn.commit()
            finally:
                conn.close()

    def load_scrape_state(self, job_key: str) -> Optional[Dict[str, Any]]:
        with self._lock:
            conn = self._conn()
            try:
                row = conn.execute(
                    "SELECT state FROM scrape_jobs WHERE job_key = ?", (job_key,)
                ).fetchone()
                if not row:
                    return None
                return json.loads(row["state"])
            except Exception:
                return None
            finally:
                conn.close()

    def clear_scrape_state(self, job_key: str) -> None:
        with self._lock:
            conn = self._conn()
            try:
                conn.execute("DELETE FROM scrape_jobs WHERE job_key = ?", (job_key,))
                conn.commit()
            finally:
                conn.close()

    def append_log(self, line: str) -> None:
        ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with self._lock:
            with open(self.log_path, "a", encoding="utf-8") as f:
                f.write(f"[{ts}] {line}\n")

    def read_log_tail(self, lines: int = 300) -> str:
        if not os.path.isfile(self.log_path):
            return ""
        try:
            with open(self.log_path, "r", encoding="utf-8") as f:
                content = f.readlines()
            return "".join(content[-lines:])
        except Exception:
            return ""

    def create_batch_run(
        self,
        batch_id: str,
        base_settings: Dict[str, Any],
        total_jobs: int,
    ) -> None:
        now = datetime.now().isoformat(timespec="seconds")
        payload = json.dumps(base_settings, ensure_ascii=False)
        with self._lock:
            conn = self._conn()
            try:
                conn.execute(
                    """
                    INSERT INTO batch_runs
                        (id, base_settings, total_jobs, completed_jobs, cancelled, started_at)
                    VALUES (?, ?, ?, 0, 0, ?)
                    """,
                    (batch_id, payload, total_jobs, now),
                )
                conn.commit()
            finally:
                conn.close()

    def update_batch_run(
        self,
        batch_id: str,
        completed_jobs: int,
        *,
        cancelled: bool = False,
    ) -> None:
        with self._lock:
            conn = self._conn()
            try:
                conn.execute(
                    """
                    UPDATE batch_runs
                    SET completed_jobs = ?, cancelled = ?
                    WHERE id = ?
                    """,
                    (completed_jobs, 1 if cancelled else 0, batch_id),
                )
                conn.commit()
            finally:
                conn.close()

    def finish_batch_run(self, batch_id: str, cancelled: bool) -> None:
        now = datetime.now().isoformat(timespec="seconds")
        with self._lock:
            conn = self._conn()
            try:
                conn.execute(
                    """
                    UPDATE batch_runs
                    SET finished_at = ?, cancelled = ?
                    WHERE id = ?
                    """,
                    (now, 1 if cancelled else 0, batch_id),
                )
                conn.commit()
            finally:
                conn.close()

    def create_batch_job(
        self,
        batch_id: str,
        *,
        job_index: int,
        transaction_type: str,
        subcategory: str,
        api_slug: str,
    ) -> int:
        now = datetime.now().isoformat(timespec="seconds")
        placeholder = json.dumps({"status": "pending"}, ensure_ascii=False)
        with self._lock:
            conn = self._conn()
            try:
                cur = conn.execute(
                    """
                    INSERT INTO batch_job_results
                        (batch_id, job_index, transaction_type, subcategory, api_slug, result_json, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (batch_id, job_index, transaction_type, subcategory, api_slug, placeholder, now),
                )
                conn.commit()
                return int(cur.lastrowid)
            finally:
                conn.close()

    def save_batch_job_result(self, job_row_id: int, result: BatchJobResult) -> None:
        now = datetime.now().isoformat(timespec="seconds")
        payload = json.dumps(result.to_dict(), ensure_ascii=False)
        with self._lock:
            conn = self._conn()
            try:
                conn.execute(
                    """
                    UPDATE batch_job_results
                    SET result_json = ?, updated_at = ?
                    WHERE id = ?
                    """,
                    (payload, now, job_row_id),
                )
                conn.commit()
            finally:
                conn.close()

    def load_batch_run_results(self, batch_id: str) -> List[BatchJobResult]:
        with self._lock:
            conn = self._conn()
            try:
                rows = conn.execute(
                    """
                    SELECT result_json FROM batch_job_results
                    WHERE batch_id = ?
                    ORDER BY job_index ASC
                    """,
                    (batch_id,),
                ).fetchall()
                results: List[BatchJobResult] = []
                for row in rows:
                    try:
                        data = json.loads(row["result_json"])
                        results.append(BatchJobResult.from_dict(data))
                    except Exception:
                        continue
                return results
            finally:
                conn.close()

    def add_scheduler_run(self, record: Dict[str, Any]) -> int:
        now = datetime.now().isoformat(timespec="seconds")
        with self._lock:
            conn = self._conn()
            try:
                cur = conn.execute(
                    """
                    INSERT INTO scheduler_runs (
                        started_at, finished_at, status,
                        province, city, district,
                        transaction_type, subcategory, search_query,
                        max_items, output_format, output_path,
                        total_posts, ok_count, duration_seconds,
                        error_message, advertiser_filter,
                        mode, jobs_total, jobs_success, jobs_failed
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        record.get("started_at") or now,
                        record.get("finished_at") or now,
                        str(record.get("status") or "unknown"),
                        str(record.get("province") or ""),
                        str(record.get("city") or ""),
                        str(record.get("district") or ""),
                        str(record.get("transaction_type") or ""),
                        str(record.get("subcategory") or ""),
                        str(record.get("search_query") or ""),
                        int(record.get("max_items") or 0),
                        str(record.get("output_format") or ""),
                        str(record.get("output_path") or ""),
                        int(record.get("total_posts") or 0),
                        int(record.get("ok_count") or 0),
                        int(record.get("duration_seconds") or 0),
                        str(record.get("error_message") or ""),
                        str(record.get("advertiser_filter") or ""),
                        str(record.get("mode") or "single"),
                        int(record.get("jobs_total") or 0),
                        int(record.get("jobs_success") or 0),
                        int(record.get("jobs_failed") or 0),
                    ),
                )
                conn.commit()
                return int(cur.lastrowid)
            finally:
                conn.close()

    def list_scheduler_runs(self, limit: int = 50) -> List[Dict[str, Any]]:
        with self._lock:
            conn = self._conn()
            try:
                rows = conn.execute(
                    """
                    SELECT * FROM scheduler_runs
                    ORDER BY COALESCE(finished_at, started_at) DESC, id DESC
                    LIMIT ?
                    """,
                    (max(1, min(int(limit), 500)),),
                ).fetchall()
                return [dict(row) for row in rows]
            finally:
                conn.close()

    def scheduler_run_stats(self) -> Dict[str, int]:
        with self._lock:
            conn = self._conn()
            try:
                row = conn.execute(
                    """
                    SELECT
                        COUNT(*) AS total,
                        SUM(CASE WHEN status = 'success' THEN 1 ELSE 0 END) AS success,
                        SUM(CASE WHEN status IN ('failed', 'cancelled') THEN 1 ELSE 0 END) AS failed,
                        SUM(COALESCE(ok_count, 0)) AS items
                    FROM scheduler_runs
                    """
                ).fetchone()
                if not row:
                    return {"total": 0, "success": 0, "failed": 0, "items": 0}
                return {
                    "total": int(row["total"] or 0),
                    "success": int(row["success"] or 0),
                    "failed": int(row["failed"] or 0),
                    "items": int(row["items"] or 0),
                }
            finally:
                conn.close()

    def clear_scheduler_runs(self) -> None:
        with self._lock:
            conn = self._conn()
            try:
                conn.execute("DELETE FROM scheduler_runs")
                conn.commit()
            finally:
                conn.close()


_storage: Optional[ExtractorStorage] = None


def get_storage() -> ExtractorStorage:
    global _storage
    if _storage is None:
        _storage = ExtractorStorage()
    return _storage
