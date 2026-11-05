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


def _run_self_test_imports() -> int:
    from app.self_test_imports import run_self_test_imports

    return run_self_test_imports()


if __name__ == "__main__":
    if "--self-test-imports" in sys.argv:
        raise SystemExit(_run_self_test_imports())

    from app.gui import run_app

    run_app()
