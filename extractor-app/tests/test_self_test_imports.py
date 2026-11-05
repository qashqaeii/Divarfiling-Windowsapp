"""Self-test-imports log and CLI flags."""
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from app.self_test_imports import run_self_test_imports


class SelfTestImportsTests(unittest.TestCase):
    def test_writes_log_file_on_success(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            log_path = str(Path(tmp) / "self-test.log")
            code = run_self_test_imports(log_path=log_path)
            self.assertEqual(code, 0)
            text = Path(log_path).read_text(encoding="utf-8")
            self.assertIn("numpy", text)
            self.assertIn("self-test-imports: PASSED", text)


if __name__ == "__main__":
    unittest.main()
