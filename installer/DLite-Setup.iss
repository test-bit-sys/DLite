; ─── DLite Installer — Inno Setup script ──────────────────────
; Professional, modern Windows installer for DLite.
; Build with:  iscc installer\DLite-Setup.iss
; Requires:    dist\DLite\  produced by PyInstaller (see build_installer.bat)

#define MyAppName        "DLite"
#define MyAppVersion     "1.0.0"
#define MyAppPublisher   "Safouane Baadoud"
#define MyAppExeName     "DLite.exe"
#define MyAppURL         "https://github.com/test-bit-sys/DLite"
#define MyAppContact     "safouanebaadoud@gmail.com"
#define WebsiteURL       "https://dlite.vercel.app"

[Setup]
; NOTE: The value of AppId uniquely identifies this application.
; Do not use the same AppId value in installers for other applications.
AppId={{B8F3E2A1-7C4D-4E9F-9A2B-1D5E7F3C8A01}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppVerName={#MyAppName} {#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}/issues
AppUpdatesURL={#MyAppURL}/releases
AppContact={#MyAppContact}
AppCopyright=Copyright (C) 2026 {#MyAppPublisher}
AppComments=Fast, Free & Open-Source Download Manager
VersionInfoVersion={#MyAppVersion}
VersionInfoCompany={#MyAppPublisher}
VersionInfoDescription=DLite — Fast, Free & Open-Source Download Manager
VersionInfoProductName={#MyAppName}
VersionInfoProductVersion={#MyAppVersion}
UninstallDisplayName={#MyAppName} {#MyAppVersion}
UninstallDisplayIcon={app}\{#MyAppExeName}
LicenseFile=..\LICENSE
DefaultDirName={autopf}\DLite
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
OutputDir=..\dist
OutputBaseFilename=DLite-Setup
SetupIconFile=..\icons\icon.ico
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
ArchitecturesAllowed=x64
ArchitecturesInstallIn64BitMode=x64
WizardImageFile=..\docs\github_social_preview.png
WizardSmallImageFile=..\icons\icon256.png
WizardImageStretch=no
ShowLanguageDialog=no
LanguageDetectionMethod=none
CloseApplications=no
RestartApplications=no
DisableWelcomePage=no
DisableReadyPage=no
Uninstallable=yes
CreateUninstallRegKey=yes

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "Create a &desktop icon"; GroupDescription: "Additional icons:"; Flags: checkedonce
Name: "startmenu"; Description: "Add to &Start menu"; GroupDescription: "Additional icons:"; Flags: checkedonce
Name: "startup"; Description: "Start {#MyAppName} when Windows starts"; GroupDescription: "Additional options:"; Flags: unchecked

[Files]
; Main application bundle produced by PyInstaller
Source: "..\dist\DLite\*"; DestDir: "{app}"; Flags: recursesubdirs createallsubdirs ignoreversion
; Bundled browser extensions + native messaging host (for easy browser setup)
Source: "..\browser-extension\*"; DestDir: "{app}\browser-extension"; Flags: recursesubdirs createallsubdirs ignoreversion
Source: "..\native_host\*"; DestDir: "{app}\native_host"; Excludes: "__pycache__"; Flags: recursesubdirs createallsubdirs ignoreversion

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: startmenu; Comment: "Launch {#MyAppName}"
Name: "{group}\Uninstall {#MyAppName}"; Filename: "{uninstallexe}"; Comment: "Remove {#MyAppName}"
Name: "{group}\{#MyAppName} Website"; Filename: "{#WebsiteURL}"; Comment: "Visit the official website"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon; Comment: "Launch {#MyAppName}"

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Launch {#MyAppName} now"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
Type: filesandordirs; Name: "{app}"

[Registry]
; Optional: run at Windows startup
Root: HKCU; Subkey: "Software\Microsoft\Windows\CurrentVersion\Run"; ValueType: string; ValueName: "DLite"; ValueData: "{app}\{#MyAppExeName}"; Flags: uninsdeletevalue; Tasks: startup
; Keep install metadata registered
Root: HKCU; Subkey: "Software\DLite"; ValueType: string; ValueName: "InstallPath"; ValueData: "{app}"; Flags: uninsdeletekey
Root: HKCU; Subkey: "Software\DLite"; ValueType: string; ValueName: "Version"; ValueData: "{#MyAppVersion}"; Flags: uninsdeletevalue

[Code]
function InitializeSetup(): Boolean;
begin
  Result := True;
end;

function InitializeUninstall(): Boolean;
begin
  Result := True;
end;