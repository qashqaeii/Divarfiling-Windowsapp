@echo off
setlocal EnableExtensions EnableDelayedExpansion
chcp 65001 >nul

set "SCRIPT_DIR=%~dp0"
cd /d "%SCRIPT_DIR%"

echo ========================================
echo   Inno Setup — DivarFilingExtractor
echo   پوشه: %SCRIPT_DIR%
echo ========================================
echo.

if not exist "app\DivarFilingExtractor.exe" (
    echo [خطا] app\DivarFilingExtractor.exe یافت نشد.
    echo ابتدا از پوشه extractor-app فایل prepare_release.bat را اجرا کنید.
    if /i not "%~1"=="nopause" pause
    exit /b 1
)

if not exist "setup.iss" (
    echo [خطا] setup.iss یافت نشد.
    if /i not "%~1"=="nopause" pause
    exit /b 1
)

set "INNO_PATH="
if exist "%LOCALAPPDATA%\Programs\Inno Setup 6\ISCC.exe" set "INNO_PATH=%LOCALAPPDATA%\Programs\Inno Setup 6\ISCC.exe"
if exist "C:\Program Files\Inno Setup 6\ISCC.exe" set "INNO_PATH=C:\Program Files\Inno Setup 6\ISCC.exe"
if exist "C:\Program Files (x86)\Inno Setup 6\ISCC.exe" set "INNO_PATH=C:\Program Files (x86)\Inno Setup 6\ISCC.exe"

if not defined INNO_PATH (
    echo [خطا] Inno Setup 6 یافت نشد.
    echo دانلود: https://jrsoftware.org/isdl.php
    if /i not "%~1"=="nopause" pause
    exit /b 1
)

echo [Inno] %INNO_PATH%
echo.

REM اعتبارسنجی مسیرهای Source داخل setup.iss
set "MISSING=0"
for %%F in (
    "app\DivarFilingExtractor.exe"
    "assets\Install.ico"
    "assets\icon.ico"
    "docs\LICENSE.txt"
    "docs\INFO_BEFORE.txt"
    "config\places-web.json"
    "fonts\B Nazanin.ttf"
) do (
    if not exist "%%~F" (
        echo   [کمبود] %%~F
        set "MISSING=1"
    )
)
if "!MISSING!"=="1" (
    echo [خطا] فایل‌های لازم برای Inno ناقص‌اند.
    if /i not "%~1"=="nopause" pause
    exit /b 1
)

if not exist "installer-out" mkdir installer-out

"%INNO_PATH%" "%SCRIPT_DIR%setup.iss"
if errorlevel 1 (
    echo [خطا] ساخت installer ناموفق بود.
    if /i not "%~1"=="nopause" pause
    exit /b 1
)

echo.
echo ✓ Installer ساخته شد:
dir /b "installer-out\*.exe" 2>nul
echo   مسیر: %SCRIPT_DIR%installer-out\
echo.
if /i not "%~1"=="nopause" pause
exit /b 0
