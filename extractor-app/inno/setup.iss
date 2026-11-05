; =============================================================================
; Inno Setup 6 — Divar Filing Extractor
; منبع اصلی: extractor-app\inno\setup.iss
; همه مسیرهای Source نسبت به پوشه release هستند (پس از prepare_release.bat).
; Compile: release\build_installer.bat   یا   ISCC.exe setup.iss
; =============================================================================

#define MyAppNameEn      "Divar Filing Extractor"
#define MyAppNameFa      "ربات استخراج فایلینگ دیوار"
#define MyAppVersion     "2.15.1"
#define MyAppPublisher   "divarfiling.ir"
#define MyAppURL         "https://divarfiling.ir/"
#define MyAppSupportURL  "https://divarfiling.ir/"
#define MyAppUpdatesURL  "https://divarfiling.ir/products/divar-extraction-bot/"
#define MyAppExeName     "DivarFilingExtractor.exe"
#define MyAppId          "{{A4E8B2C1-9F3D-4A6E-B8C7-1D2E3F4A5B6C}"

[Setup]
; --- هویت ---
AppId={#MyAppId}
AppName={#MyAppNameEn}
AppVersion={#MyAppVersion}
AppVerName={#MyAppNameEn} {#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppSupportURL}
AppUpdatesURL={#MyAppUpdatesURL}
AppCopyright=Copyright (C) {#MyAppPublisher}
VersionInfoVersion={#MyAppVersion}.0
VersionInfoCompany={#MyAppPublisher}
VersionInfoDescription={#MyAppNameEn}
VersionInfoProductName={#MyAppNameEn}
VersionInfoProductVersion={#MyAppVersion}.0
VersionInfoCopyright=Copyright (C) {#MyAppPublisher}
VersionInfoOriginalFileName=DivarFilingExtractor_Setup_{#MyAppVersion}.exe

; --- مسیر نصب ---
; PrivilegesRequired=lowest → {autopf} = %LocalAppData%\Programs (قابل نوشتن برای config/output)
; با dialog کاربر می‌تواند نصب مدیر را در Program Files انتخاب کند
DefaultDirName={autopf}\DivarFilingExtractor
DefaultGroupName={#MyAppNameEn}
DisableProgramGroupPage=yes
UsePreviousAppDir=yes
DirExistsWarning=auto
AllowNoIcons=yes

; --- معماری ---
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
MinVersion=10.0

; --- دسترسی ---
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog

; --- خروجی Setup ---
OutputDir=installer-out
OutputBaseFilename=DivarFilingExtractor_Setup_{#MyAppVersion}
SetupIconFile=assets\Install.ico
UninstallDisplayIcon={app}\assets\icon.ico
UninstallDisplayName={#MyAppNameEn} {#MyAppVersion}

; --- فشرده‌سازی و ظاهر ---
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern
WizardSizePercent=120
DisableWelcomePage=no

; --- پایداری نصب ---
AppMutex=DivarFilingExtractor_SingleInstance
CloseApplications=yes
CloseApplicationsFilter=DivarFilingExtractor.exe
RestartApplications=no
SetupLogging=yes

; --- مستندات ویزارد ---
LicenseFile=docs\LICENSE.txt
InfoBeforeFile=docs\INFO_BEFORE.txt

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Dirs]
; پوشه‌های قابل‌نوشتن کنار exe (paths.py → config\app_data و output)
Name: "{app}\config"; Permissions: users-modify
Name: "{app}\config\app_data"; Permissions: users-modify
Name: "{app}\output"; Permissions: users-modify

[Files]
; اجرایی — onefile PyInstaller
Source: "app\{#MyAppExeName}"; DestDir: "{app}"; Flags: ignoreversion

; برند و آیکن‌ها
Source: "assets\icon.ico"; DestDir: "{app}\assets"; Flags: ignoreversion
Source: "assets\icon.png"; DestDir: "{app}\assets"; Flags: ignoreversion
Source: "assets\logo.png"; DestDir: "{app}\assets"; Flags: ignoreversion
Source: "assets\Install.ico"; DestDir: "{app}\assets"; Flags: ignoreversion
Source: "assets\icons\*"; DestDir: "{app}\assets\icons"; Flags: ignoreversion recursesubdirs createallsubdirs

; فونت فارسی
Source: "fonts\*"; DestDir: "{app}\fonts"; Flags: ignoreversion recursesubdirs createallsubdirs

; پیکربندی — onlyifdoesntexist تا تنظیمات کاربر حفظ شود
Source: "config\places-web.json"; DestDir: "{app}\config"; Flags: ignoreversion onlyifdoesntexist
Source: "config\settings.example.json"; DestDir: "{app}\config"; Flags: ignoreversion

[Icons]
Name: "{autoprograms}\{#MyAppNameEn}"; Filename: "{app}\{#MyAppExeName}"; IconFilename: "{app}\assets\icon.ico"; Comment: "{#MyAppNameFa}"
Name: "{autodesktop}\{#MyAppNameEn}"; Filename: "{app}\{#MyAppExeName}"; IconFilename: "{app}\assets\icon.ico"; Comment: "{#MyAppNameFa}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppNameEn, '&', '&&')}}"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
; فقط کش موقت — خروجی کاربر و app_data عمداً پاک نمی‌شوند
Type: filesandordirs; Name: "{app}\config\app_data\cache"
Type: filesandordirs; Name: "{app}\config\app_data\tmp"
