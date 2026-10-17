@echo off
setlocal EnableExtensions EnableDelayedExpansion
chcp 65001 >nul

set "SCRIPT_DIR=%~dp0"
set "REPO_ROOT=%SCRIPT_DIR%.."
cd /d "%SCRIPT_DIR%"

echo ========================================
echo   ساخت DivarFilingExtractor.exe (onefile)
echo ========================================
echo.

where python >nul 2>&1
if errorlevel 1 (
    echo [خطا] Python یافت نشد. Python 3.10+ را نصب کنید.
    pause
    exit /b 1
)

echo [1/4] نصب وابستگی‌های build...
python -m pip install -r requirements-build.txt
if errorlevel 1 (
    echo [خطا] نصب وابستگی‌ها ناموفق بود.
    pause
    exit /b 1
)

call "%SCRIPT_DIR%sync_assets.bat"
if errorlevel 1 (
    echo [خطا] همگام‌سازی assets ناموفق بود.
    pause
    exit /b 1
)

echo.
echo [2/4] PyInstaller — onefile ...
python -m PyInstaller --noconfirm --clean divar_extractor.spec
if errorlevel 1 (
    echo [خطا] ساخت exe ناموفق بود.
    pause
    exit /b 1
)

echo.
echo [3/4] آماده‌سازی پوشه release برای Inno Setup ...
call "%SCRIPT_DIR%prepare_release.bat" nopause
if errorlevel 1 exit /b 1

echo.
echo ✓ exe: %SCRIPT_DIR%dist\DivarFilingExtractor.exe
echo ✓ بسته Inno Setup: %SCRIPT_DIR%release\
echo.
echo مرحله بعد:
echo   release\build_installer.bat
echo.
if /i not "%~1"=="nopause" pause
