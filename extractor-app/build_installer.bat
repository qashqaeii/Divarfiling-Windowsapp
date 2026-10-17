@echo off
setlocal EnableExtensions EnableDelayedExpansion
chcp 65001 >nul

set "SCRIPT_DIR=%~dp0"
cd /d "%SCRIPT_DIR%"

echo ========================================
echo   Inno Setup — DivarFilingExtractor
echo ========================================
echo.

if not exist "release\app\DivarFilingExtractor.exe" (
    echo [اطلاع] پوشه release خالی است — در حال آماده‌سازی...
    call "%SCRIPT_DIR%prepare_release.bat" nopause
    if errorlevel 1 (
        pause
        exit /b 1
    )
)

call "%SCRIPT_DIR%release\build_installer.bat" %*
if /i not "%~1"=="nopause" (
    if errorlevel 1 pause
)
