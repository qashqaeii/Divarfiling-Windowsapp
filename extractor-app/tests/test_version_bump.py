"""Light check: Windows app version 2.15.1 consistency."""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_version_bump_2_15_1() -> None:
    tokens = (ROOT / "app/ui/tokens.py").read_text(encoding="utf-8")
    app_ver = re.search(r'APP_VERSION = "([^"]+)"', tokens)
    assert app_ver, "APP_VERSION missing"
    assert app_ver.group(1) == "2.15.1"

    for rel in ("inno/setup.iss", "release/setup.iss"):
        text = (ROOT / rel).read_text(encoding="utf-8")
        m = re.search(r'#define MyAppVersion\s+"([^"]+)"', text)
        assert m and m.group(1) == "2.15.1", rel

    vi = (ROOT / "build/version_info.txt").read_text(encoding="utf-8")
    assert "filevers=(2, 15, 1, 0)" in vi
    assert "ProductVersion', u'2.15.1.0'" in vi

    spec = (ROOT / "divar_extractor.spec").read_text(encoding="utf-8")
    assert 'ext_path("build", "version_info.txt")' in spec
    assert "version=_version_info" in spec

    for rel in ("inno/docs/INFO_BEFORE.txt", "release/docs/INFO_BEFORE.txt"):
        assert "2.15.1" in (ROOT / rel).read_text(encoding="utf-8")


if __name__ == "__main__":
    test_version_bump_2_15_1()
    print("version bump check OK: 2.15.1")
