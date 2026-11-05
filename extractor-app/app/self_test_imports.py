"""
Self-test for frozen EXE: import critical libraries without GUI or network.
Used in CI and for diagnosing DLL / PyInstaller packaging issues.
"""
from __future__ import annotations

import sys
import traceback


def _ensure_console_on_frozen_windows() -> None:
    if not getattr(sys, "frozen", False) or sys.platform != "win32":
        return
    try:
        import ctypes

        kernel32 = ctypes.windll.kernel32  # type: ignore[attr-defined]
        if kernel32.GetConsoleWindow() == 0:
            kernel32.AllocConsole()
            sys.stdout = open("CONOUT$", "w", encoding="utf-8", errors="replace")  # noqa: SIM115
            sys.stderr = open("CONOUT$", "w", encoding="utf-8", errors="replace")  # noqa: SIM115
    except Exception:
        pass


def _run_check(label: str) -> str:
    if label == "numpy":
        import numpy as np

        return np.__version__
    if label == "pandas":
        import pandas as pd

        return pd.__version__
    if label == "openpyxl":
        import openpyxl

        return openpyxl.__version__
    if label == "PIL":
        from PIL import Image

        return Image.__version__
    if label == "customtkinter":
        import customtkinter

        return customtkinter.__version__
    if label == "requests":
        import requests

        return requests.__version__
    if label == "jdatetime":
        import jdatetime

        return getattr(jdatetime, "__version__", "ok")
    if label == "keyring":
        import keyring

        return getattr(keyring, "__version__", "ok")
    if label == "app.extraction_engine":
        from app import extraction_engine

        return extraction_engine.__name__
    if label == "app.extraction_job":
        from app import extraction_job

        return extraction_job.__name__
    if label == "app.license_client":
        from app import license_client

        return license_client.__name__
    if label == "app.platform_upload":
        from app import platform_upload

        return platform_upload.__name__
    if label == "app.places":
        from app import places

        return places.__name__
    if label == "export_divar_items":
        import export_divar_items

        return export_divar_items.__name__
    if label == "divar_location":
        import divar_location

        return getattr(divar_location, "__version__", divar_location.__name__)
    raise ValueError(f"unknown check: {label}")


_IMPORT_CHECKS: list[str] = [
    "numpy",
    "pandas",
    "openpyxl",
    "PIL",
    "customtkinter",
    "requests",
    "jdatetime",
    "keyring",
    "app.extraction_engine",
    "app.extraction_job",
    "app.license_client",
    "app.platform_upload",
    "app.places",
    "export_divar_items",
    "divar_location",
]


def run_self_test_imports() -> int:
    """Return 0 on success, 1 on any import failure."""
    _ensure_console_on_frozen_windows()
    print("Divar Filing Extractor — self-test-imports")
    print(f"Python: {sys.version.split()[0]}")
    print(f"Frozen: {getattr(sys, 'frozen', False)}")
    print("---")
    failed = False
    for label in _IMPORT_CHECKS:
        try:
            ver = _run_check(label)
            print(f"OK  {label}  ({ver})")
        except Exception as exc:
            failed = True
            print(f"FAIL  {label}: {exc}")
            traceback.print_exc()
    print("---")
    if failed:
        print("self-test-imports: FAILED")
        return 1
    print("self-test-imports: PASSED")
    return 0
