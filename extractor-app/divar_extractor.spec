# -*- mode: python ; coding: utf-8 -*-
# PyInstaller — اپ استخراج دیوار (onefile)
# اجرا از پوشه extractor-app:  python -m PyInstaller --noconfirm --clean divar_extractor.spec

import os

import customtkinter

block_cipher = None

# SPECPATH = پوشه حاوی این فایل (extractor-app)
EXTRACTOR_ROOT = SPECPATH
REPO_ROOT = os.path.dirname(EXTRACTOR_ROOT)

ct_assets = os.path.join(os.path.dirname(customtkinter.__file__), "assets")


def repo_path(*parts: str) -> str:
    return os.path.join(REPO_ROOT, *parts)


def ext_path(*parts: str) -> str:
    return os.path.join(EXTRACTOR_ROOT, *parts)


def data_if_exists(src: str, dest: str) -> list:
    if os.path.isfile(src) or os.path.isdir(src):
        return [(src, dest)]
    print(f"[spec] skip missing data: {src}")
    return []


datas_list: list = []

# برند — اولویت با assets داخل extractor-app
_assets_root = ext_path("assets")
for _name in ("icon.ico", "icon.png", "logo.png", "Install.ico"):
    _src = os.path.join(_assets_root, _name)
    if not os.path.isfile(_src):
        _src = repo_path("assets", _name)
    if os.path.isfile(_src):
        datas_list.append((_src, "assets"))
    else:
        print(f"[spec] WARNING: missing asset {_name}")

datas_list.extend(data_if_exists(repo_path("fonts", "B Nazanin.ttf"), "fonts"))
datas_list.extend(data_if_exists(repo_path("fonts", "B Nazanin Bold.ttf"), "fonts"))
datas_list.extend(data_if_exists(repo_path("config", "places-web.json"), "config"))
datas_list.extend(data_if_exists(ext_path("config", "settings.example.json"), "config"))
datas_list.extend(data_if_exists(ct_assets, "customtkinter/assets"))

# آیکن‌های UI — DestDir باید پوشه باشد نه مسیر فایل
_icons_dir = ext_path("assets", "icons")
if os.path.isdir(_icons_dir):
    for _fname in os.listdir(_icons_dir):
        if _fname.lower().endswith(".png"):
            datas_list.append((os.path.join(_icons_dir, _fname), "assets/icons"))

_icon_ico = ext_path("assets", "icon.ico")
if not os.path.isfile(_icon_ico):
    _icon_ico = repo_path("assets", "icon.ico")

_version_info = ext_path("build", "version_info.txt")

a = Analysis(
    [ext_path("main.py")],
    pathex=[
        EXTRACTOR_ROOT,
        ext_path("app"),
        repo_path("src"),
    ],
    binaries=[],
    datas=datas_list,
    hiddenimports=[
        "app",
        "app.brand",
        "app.constants",
        "app.extraction_engine",
        "app.formatters",
        "app.gui",
        "app.license_client",
        "app.desktop_auth_client",
        "app.credential_store",
        "app.notifications",
        "app.ui.components.account_login_panel",
        "app.ui.components.license_selection_dialog",
        "keyring",
        "keyring.backends",
        "keyring.backends.Windows",
        "app.platform_upload",
        "app.paths",
        "app.places",
        "app.scheduler",
        "app.shutdown_manager",
        "app.storage",
        "app.system_tray",
        "app.theme",
        "app.tray_settings",
        "app.ui",
        "app.ui.components",
        "app.ui.components.license_account_panel",
        "app.ui.components.tray_close_dialog",
        "app.ui.pages",
        "app.ui.tokens",
        "app.ui.typography",
        "app.ui.theme",
        "app.ui.platform_icons",
        "app.filter_utils",
        "app.ui_components",
        "app.widgets",
        "customtkinter",
        "PIL",
        "PIL.Image",
        "PIL.ImageDraw",
        "PIL.ImageTk",
        "pystray",
        "pystray._win32",
        "export_divar_items",
        "advertiser_signal",
        "license_core",
        "requests",
        "urllib3",
        "urllib3.util",
        "urllib3.util.retry",
        "requests.adapters",
        "certifi",
        "charset_normalizer",
        "idna",
        "pandas",
        "pandas._libs.tslibs.timedeltas",
        "pandas._libs.tslibs.nattype",
        "pandas._libs.tslibs.np_datetime",
        "openpyxl",
        "openpyxl.cell._writer",
        "numpy",
        "jdatetime",
        "winotify",
        "sqlite3",
        "tkinter",
        "tkinter.font",
        "tkinter.messagebox",
        "concurrent.futures",
        "queue",
        "json",
        "threading",
        "ctypes",
        "hashlib",
        "platform",
        "webbrowser",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        "matplotlib",
        "scipy",
        "pytest",
        "IPython",
        "django",
        "pyarrow",
        "sqlalchemy",
        "psycopg2",
        "psycopg",
        "gevent",
        "numba",
        "llvmlite",
        "folium",
        "branca",
        "xyzservices",
        "bokeh",
        "plotly",
        "dash",
        "flask",
        "fastapi",
        "uvicorn",
        "jupyter",
        "notebook",
        "ipykernel",
        "zmq",
        "tornado",
        "selenium",
        "playwright",
        "torch",
        "tensorflow",
        "sklearn",
        "scikit-learn",
        "cv2",
        "opencv",
        "PyQt5",
        "PyQt6",
        "PySide2",
        "PySide6",
        "wx",
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name="DivarFilingExtractor",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=_icon_ico if os.path.isfile(_icon_ico) else None,
    version=_version_info if os.path.isfile(_version_info) else None,
)
