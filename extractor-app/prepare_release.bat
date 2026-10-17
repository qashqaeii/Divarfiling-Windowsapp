@echo off
setlocal EnableExtensions EnableDelayedExpansion
chcp 65001 >nul

set "SCRIPT_DIR=%~dp0"
set "REPO_ROOT=%SCRIPT_DIR%.."
set "RELEASE=%SCRIPT_DIR%release"
cd /d "%SCRIPT_DIR%"

echo ========================================
echo   آماده‌سازی پوشه release برای Inno Setup
echo ========================================
echo.

if not exist "dist\DivarFilingExtractor.exe" (
    echo [خطا] dist\DivarFilingExtractor.exe یافت نشد.
    echo ابتدا build_exe.bat را اجرا کنید.
    if /i not "%~1"=="nopause" pause
    exit /b 1
)

call "%SCRIPT_DIR%sync_assets.bat"
if errorlevel 1 (
    if /i not "%~1"=="nopause" pause
    exit /b 1
)

if not exist "%RELEASE%" mkdir "%RELEASE%"

echo [1/5] پاک‌سازی محتوای release...
for %%D in (app assets fonts config output docs installer-out) do (
    if exist "%RELEASE%\%%D" rmdir /s /q "%RELEASE%\%%D"
)
if exist "%RELEASE%\DivarFilingExtractor.exe" del /q "%RELEASE%\DivarFilingExtractor.exe" >nul 2>&1

echo [2/5] ساخت پوشه‌ها...
mkdir "%RELEASE%\app"
mkdir "%RELEASE%\assets"
mkdir "%RELEASE%\assets\icons"
mkdir "%RELEASE%\fonts"
mkdir "%RELEASE%\config"
mkdir "%RELEASE%\config\app_data"
mkdir "%RELEASE%\output"
mkdir "%RELEASE%\docs"
mkdir "%RELEASE%\installer-out"

echo [3/5] کپی فایل‌ها...
copy /y "dist\DivarFilingExtractor.exe" "%RELEASE%\app\" >nul
if errorlevel 1 (
    echo [خطا] کپی exe ناموفق بود.
    if /i not "%~1"=="nopause" pause
    exit /b 1
)

xcopy /E /I /Y "%SCRIPT_DIR%assets\*" "%RELEASE%\assets\" >nul

if not exist "%REPO_ROOT%\fonts\B Nazanin.ttf" (
    echo [خطا] فونت یافت نشد: %REPO_ROOT%\fonts\B Nazanin.ttf
    if /i not "%~1"=="nopause" pause
    exit /b 1
)
copy /y "%REPO_ROOT%\fonts\*.ttf" "%RELEASE%\fonts\" >nul

if not exist "%REPO_ROOT%\config\places-web.json" (
    echo [خطا] places-web.json یافت نشد.
    if /i not "%~1"=="nopause" pause
    exit /b 1
)
copy /y "%REPO_ROOT%\config\places-web.json" "%RELEASE%\config\" >nul
copy /y "config\settings.example.json" "%RELEASE%\config\" >nul

REM مستندات Inno — اولویت با inno\docs سپس installer ریشه
if exist "%SCRIPT_DIR%inno\docs\LICENSE.txt" (
    copy /y "%SCRIPT_DIR%inno\docs\LICENSE.txt" "%RELEASE%\docs\" >nul
) else if exist "%REPO_ROOT%\installer\LICENSE.txt" (
    copy /y "%REPO_ROOT%\installer\LICENSE.txt" "%RELEASE%\docs\" >nul
)

if exist "%SCRIPT_DIR%inno\docs\INFO_BEFORE.txt" (
    copy /y "%SCRIPT_DIR%inno\docs\INFO_BEFORE.txt" "%RELEASE%\docs\" >nul
) else if exist "%REPO_ROOT%\installer\INFO_BEFORE.txt" (
    copy /y "%REPO_ROOT%\installer\INFO_BEFORE.txt" "%RELEASE%\docs\" >nul
)

echo. > "%RELEASE%\output\.gitkeep"
echo. > "%RELEASE%\config\app_data\.gitkeep"

echo [4/5] اعتبارسنجی فایل‌های ضروری...
set "MISSING=0"
for %%F in (
    "app\DivarFilingExtractor.exe"
    "assets\icon.ico"
    "assets\icon.png"
    "assets\logo.png"
    "assets\Install.ico"
    "fonts\B Nazanin.ttf"
    "fonts\B Nazanin Bold.ttf"
    "config\places-web.json"
    "config\settings.example.json"
    "docs\LICENSE.txt"
    "docs\INFO_BEFORE.txt"
) do (
    if not exist "%RELEASE%\%%~F" (
        echo   [کمبود] %%~F
        set "MISSING=1"
    )
)

set "ICON_COUNT=0"
for %%F in ("%RELEASE%\assets\icons\*.png") do set /a ICON_COUNT+=1
if "!ICON_COUNT!"=="0" (
    echo   [کمبود] assets\icons\*.png
    set "MISSING=1"
)

if "!MISSING!"=="1" (
    echo.
    echo [خطا] برخی فایل‌های ضروری در release نیستند — build متوقف شد.
    if /i not "%~1"=="nopause" pause
    exit /b 1
)

echo [5/5] به‌روزرسانی اسکریپت Inno Setup...
copy /y "%SCRIPT_DIR%inno\setup.iss" "%RELEASE%\setup.iss" >nul
copy /y "%SCRIPT_DIR%inno\build_installer.bat" "%RELEASE%\build_installer.bat" >nul
copy /y "%SCRIPT_DIR%inno\README.txt" "%RELEASE%\README.txt" >nul

echo.
echo ✓ پوشه release آماده است: %RELEASE%
echo   exe:          %RELEASE%\app\DivarFilingExtractor.exe
echo   icons PNG:    !ICON_COUNT!
echo   setup.iss:    %RELEASE%\setup.iss
echo.
if /i not "%~1"=="nopause" pause
exit /b 0
