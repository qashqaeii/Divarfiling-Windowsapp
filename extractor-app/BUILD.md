# ساخت exe و فایل نصب — اپ استخراج

## پیش‌نیاز

- **Python 3.10+** (در PATH)
- **Inno Setup 6** — [دانلود](https://jrsoftware.org/isdl.php)
  - مسیرهای پشتیبانی‌شده:  
    `C:\Program Files (x86)\Inno Setup 6\ISCC.exe`  
    `C:\Program Files\Inno Setup 6\ISCC.exe`  
    `%LOCALAPPDATA%\Programs\Inno Setup 6\ISCC.exe`

## ساخت یک‌مرحله‌ای (پیشنهادی)

از پوشه `extractor-app`:

```bat
build_all.bat
```

خروجی:

| فایل | مسیر |
|------|------|
| exe تک‌فایلی | `dist\DivarFilingExtractor.exe` |
| نصب‌کننده | `release\installer-out\DivarFilingExtractor_Setup_2.15.0.exe` |

## ساخت مرحله‌به‌مرحله

### ۱) exe با PyInstaller (onefile)

```bat
build_exe.bat
```

- نصب `requirements-build.txt` (شامل PyInstaller)
- اجرای `divar_extractor.spec`
- کپی خودکار به `release\` با `prepare_release.bat`

### ۲) فایل نصب با Inno Setup

```bat
build_installer.bat
```

یا فقط از داخل `release`:

```bat
release\build_installer.bat
```

## ساختار پوشه release

```
release/
  app/DivarFilingExtractor.exe
  assets/          آیکن‌ها + icons/
  fonts/           فونت فارسی
  config/          places-web.json، settings.example.json
  output/          پوشه خروجی خالی
  docs/            LICENSE، INFO_BEFORE
  setup.iss        اسکریپت Inno (کپی از inno/setup.iss)
  installer-out/   خروجی Setup.exe
```

## مسیر نصب پیش‌فرض

با `PrivilegesRequired=lowest` مسیر پیش‌فرض:

`%LocalAppData%\Programs\DivarFilingExtractor`

این مسیر برای نوشتن `config\app_data` و `output` کنار exe مناسب است.  
کاربر می‌تواند در ویزارد، نصب با دسترسی مدیر در Program Files را انتخاب کند.

## ویرایش نسخه

نسخه فعلی اپ در `app\ui\tokens.py` → `APP_VERSION` است. همزمان به‌روز کنید:

1. `app\ui\tokens.py` — `APP_VERSION`
2. `build\version_info.txt` — نسخه exe در ویندوز
3. `inno\setup.iss` — `#define MyAppVersion`

بعد از ویرایش `inno\setup.iss`، `prepare_release.bat` آن را به `release` کپی می‌کند.

## عیب‌یابی

| خطا | راه‌حل |
|-----|--------|
| Python یافت نشد | Python را نصب و به PATH اضافه کنید |
| Inno Setup یافت نشد | Inno Setup 6 را نصب کنید |
| exe یافت نشد در release | ابتدا `build_exe.bat` را اجرا کنید |
| کمبود فایل در release | خروجی `prepare_release.bat` را ببینید |
| PyInstaller خطا | `pip install -r requirements-build.txt` |

## فایل‌های مرجع

- `divar_extractor.spec` — تنظیمات PyInstaller (onefile، آیکن، داده‌ها)
- `inno\setup.iss` — تنظیمات نصب‌کننده (منبع اصلی)
- `inno\docs\` — LICENSE و INFO_BEFORE مخصوص اپ استخراج
- `prepare_release.bat` — همگام‌سازی `release` با `dist`

## ساخت در GitHub Actions

برای ساخت بدون نصب محلی Python/Inno روی CI:

1. در GitHub به ریپازیتوری `Divarfiling-Windowsapp` بروید.
2. تب **Actions** → Workflow **Build Windows EXE & Inno Setup**.
3. **Run workflow** → شاخه `main` → **Run workflow**.
4. پس از اتمام Run سبز، در همان Run بخش **Artifacts** را باز کنید:
   - **DivarFiling-Windows-EXE** — `DivarFilingExtractor.exe` (قابل اجرا بدون نصب) + `build-manifest.txt`
   - **DivarFiling-Windows-Setup** — `DivarFilingExtractor_Setup_<version>.exe` (نصب‌کننده برای کاربران) + manifest
5. نسخه خروجی از `app\ui\tokens.py` (`APP_VERSION`) و `inno\setup.iss` (`MyAppVersion`) گرفته می‌شود؛ هر دو باید یکسان باشند.
6. در صورت خطا، لاگ Stepهای **Build EXE** و **Build installer** را ببینید؛ manifest شامل SHA256 و SHA commit است.

فایل YAML: `.github/workflows/build-windows.yml` (Runner: `windows-2022`, Python 3.11).
