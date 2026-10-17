پوشه release — بسته نصب Inno Setup
====================================

این پوشه شامل همه فایل‌های لازم برای ساخت installer است.
مسیرها در setup.iss همگی نسبی و داخل همین پوشه هستند.

ساختار:
  app\DivarFilingExtractor.exe   — فایل اجرایی onefile
  assets\                        — آیکن‌ها (+ icons\)
  fonts\                         — فونت‌های فارسی
  config\                        — places-web.json و settings.example.json
  output\                        — پوشه خالی خروجی (بعد از نصب)
  docs\                          — LICENSE و INFO_BEFORE
  setup.iss                      — اسکریپت Inno Setup
  build_installer.bat            — کامپایل installer
  installer-out\                 — خروجی Setup.exe

مسیر نصب پیش‌فرض:
  %LocalAppData%\Programs\DivarFilingExtractor

به‌روزرسانی:
  1) از پوشه extractor-app: prepare_release.bat
  2) سپس: release\build_installer.bat

ویرایش setup.iss:
  فایل اصلی در inno\setup.iss است؛ prepare_release.bat آن را اینجا کپی می‌کند.
