@echo off
setlocal EnableExtensions EnableDelayedExpansion
chcp 65001 >nul

set "SCRIPT_DIR=%~dp0"
cd /d "%SCRIPT_DIR%"

echo ========================================
echo   ساخت کامل — exe onefile + نصب Inno
echo ========================================
echo.
echo مراحل:
echo   1) PyInstaller — DivarFilingExtractor.exe
echo   2) آماده‌سازی پوشه release
echo   3) Inno Setup — فایل نصب Setup.exe
echo.

call "%SCRIPT_DIR%build_exe.bat" nopause
if errorlevel 1 (
    echo.
    echo [خطا] ساخت exe متوقف شد.
    pause
    exit /b 1
)

call "%SCRIPT_DIR%build_installer.bat" nopause
if errorlevel 1 (
    echo.
    echo [خطا] ساخت installer متوقف شد.
    pause
    exit /b 1
)

echo.
echo ========================================
echo   ✓ ساخت کامل انجام شد
echo ========================================
echo.
echo   exe:        %SCRIPT_DIR%dist\DivarFilingExtractor.exe
echo   installer:  %SCRIPT_DIR%release\installer-out\
dir /b "%SCRIPT_DIR%release\installer-out\*.exe" 2>nul
echo.
pause
