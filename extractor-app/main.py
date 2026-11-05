"""
دیوار · اپ استخراج حرفه‌ای (مستقل)
Entry point — پوشه جدا از اپ اصلی
"""
from __future__ import annotations

import os
import sys

if getattr(sys, "frozen", False):
    APP_ROOT = os.path.dirname(os.path.abspath(sys.executable))
else:
    APP_ROOT = os.path.dirname(os.path.abspath(__file__))
    PARENT_SRC = os.path.join(os.path.dirname(APP_ROOT), "src")
    for path in (APP_ROOT, os.path.join(APP_ROOT, "app"), PARENT_SRC):
        if path not in sys.path:
            sys.path.insert(0, path)

os.chdir(APP_ROOT)


def _parse_self_test_log(argv: list[str]) -> str | None:
    for index, arg in enumerate(argv):
        if arg == "--self-test-log" and index + 1 < len(argv):
            return argv[index + 1]
        if arg.startswith("--self-test-log="):
            return arg.split("=", 1)[1]
    return None


def _run_self_test_imports(log_path: str | None = None) -> int:
    from app.self_test_imports import run_self_test_imports

    return run_self_test_imports(log_path=log_path)


if __name__ == "__main__":
    if "--self-test-imports" in sys.argv:
        raise SystemExit(_run_self_test_imports(_parse_self_test_log(sys.argv)))

    from app.gui import run_app

    run_app()
