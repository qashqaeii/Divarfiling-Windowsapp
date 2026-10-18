# -*- coding: utf-8 -*-
"""تست‌های hotfix export فروش / retry / UI outcome (بدون شبکه دیوار)."""
from __future__ import annotations

import os
import sys
import tempfile
import unittest
from unittest.mock import MagicMock, patch

_EXTRACTOR_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_REPO_SRC = os.path.join(os.path.dirname(_EXTRACTOR_ROOT), "src")
for path in (_EXTRACTOR_ROOT, os.path.join(_EXTRACTOR_ROOT, "app"), _REPO_SRC):
    if path not in sys.path:
        sys.path.insert(0, path)

import pandas as pd
from export_divar_items import CONFIG, export_to_excel

from app.batch_models import JobStatus, UploadStatus
from app.extraction_engine import ExtractionEngine
from app.extraction_job import ExtractionJobService
from app.places import PlacesManager
from app.retry_utils import NonRetryableExtractionError, run_with_retry


def _sell_row(i: int) -> dict:
    return {
        "token": f"sell{i}",
        "title": f"sell {i}",
        "share_link": f"https://divar.ir/v/sell{i}",
        "مکان_شهر": "چالوس",
        "مکان_منطقه": "test",
        "دسته‌بندی_عنوان": "فروش آپارتمان",
        "attributes": "متراژ:50|ساخت:1400",
        "انتشار_unavailable_after": "2026-07-18T12:00:00",
        "مالی_قیمت_کل_عدد": 5_000_000_000,
        "مالی_قیمت_هر_متر_عدد": 100_000_000,
    }


class TestExportSell(unittest.TestCase):
    def test_a_export_34_sell_rows(self):
        CONFIG["category"] = "apartment-sell"
        rows = [_sell_row(i) for i in range(34)]
        tmp = tempfile.mktemp(suffix=".xlsx")
        try:
            path = export_to_excel(rows, tmp)
            self.assertTrue(os.path.isfile(path))
            df = pd.read_excel(path)
            self.assertEqual(len(df), 34)
        finally:
            if os.path.exists(tmp):
                os.remove(tmp)

    def test_b_rent_then_sell_paths(self):
        engine = ExtractionEngine(
            MagicMock(),
            PlacesManager(),
            MagicMock(),
            on_log=lambda *a, **k: None,
            on_progress=lambda *a, **k: None,
            is_cancelled=lambda: False,
        )
        base = {
            "province": "مازندران",
            "city": "چالوس",
            "district": "",
            "subcategory": "آپارتمان",
            "output_format": "excel",
        }
        rent_settings = {**base, "transaction_type": "اجاره مسکونی"}
        sell_settings = {**base, "transaction_type": "فروش مسکونی"}
        rent_path = engine.build_output_path(rent_settings)
        sell_path = engine.build_output_path(sell_settings)
        self.assertNotEqual(os.path.normcase(rent_path), os.path.normcase(sell_path))
        self.assertIn("اجاره", rent_path)
        self.assertIn("فروش", sell_path)


class TestRetryAndExport(unittest.TestCase):
    def test_d_export_error_not_retried(self):
        calls = {"n": 0}

        def op():
            calls["n"] += 1
            raise NonRetryableExtractionError("boom", stage="excel")

        with self.assertRaises(NonRetryableExtractionError):
            run_with_retry(op, is_retryable=lambda e: not isinstance(e, NonRetryableExtractionError))
        self.assertEqual(calls["n"], 1)

    def test_e_upload_failed_keeps_file(self):
        engine = MagicMock()
        engine.run.return_value = "/tmp/out.xlsx"
        engine.storage = MagicMock()
        license_client = MagicMock()
        places = PlacesManager()
        logs = []

        service = ExtractionJobService(
            engine,
            license_client,
            places,
            on_log=lambda msg, tone: logs.append((msg, tone)),
            is_cancelled=lambda: False,
        )
        with patch(
            "app.extraction_job.upload_extraction_file_with_retry",
            return_value={"success": False, "error": "mock fail"},
        ):
            result = service.run(
                {"upload_to_platform": True, "max_items": 1},
                transaction_type="فروش مسکونی",
                subcategory="آپارتمان",
                api_slug="apartment-sell",
            )
        self.assertEqual(result.output_path, "/tmp/out.xlsx")
        self.assertEqual(result.upload_status, UploadStatus.FAILED)
        self.assertEqual(result.extraction_status, JobStatus.SUCCESS)


if __name__ == "__main__":
    unittest.main()
