@echo off
setlocal EnableExtensions EnableDelayedExpansion
chcp 65001 >nul

set "SCRIPT_DIR=%~dp0"
set "REPO_ROOT=%SCRIPT_DIR%.."
set "ASSETS=%SCRIPT_DIR%assets"
set "ICONS=%ASSETS%\icons"

if not exist "%ASSETS%" mkdir "%ASSETS%"
if not exist "%ICONS%" mkdir "%ICONS%"

echo [sync] همگام‌سازی آیکن‌های برند...
for %%F in (icon.ico icon.png Install.ico logo.png) do (
    if exist "%REPO_ROOT%\assets\%%F" (
        copy /y "%REPO_ROOT%\assets\%%F" "%ASSETS%\" >nul
        echo   + %%F
    )
)

echo [sync] بررسی آیکن‌های UI (assets\icons)...
set "COUNT=0"
for %%F in ("%ICONS%\*.png") do set /a COUNT+=1

if "!COUNT!"=="0" (
    echo [sync] کپی از mobile drawable-nodpi...
    set "SRC=%REPO_ROOT%\divar-mobile-app\android\app\src\main\res\drawable-nodpi"
    if exist "!SRC!" (
        for %%F in (api_documentation automation bar_chart bell building calendar clipboard_list coins copy database download external_link file_text filter folder handshake help_center layout_grid list_todo map_pin phone rocket rotate_ccw search settings sparkles theme_switch timer upload user zap) do (
            if exist "!SRC!\%%F.png" (
                copy /y "!SRC!\%%F.png" "%ICONS%\" >nul
            )
        )
    )
    set "COUNT=0"
    for %%F in ("%ICONS%\*.png") do set /a COUNT+=1
)

echo [sync] تعداد آیکن PNG: !COUNT!
if "!COUNT!"=="0" (
    echo [خطا] هیچ آیکن PNG در assets\icons نیست.
    exit /b 1
)
exit /b 0
