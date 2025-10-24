; ==========================================
; 🔐 CodePass Installer — Inno Setup Script
; ==========================================

#define MyAppName "CodePass"
#define MyAppVersion "2.1.7"            ; <- wpisz tu aktualną wersję
#define MyAppPublisher "codepass0v12"
#define MyAppExeName "CodePass.exe"

; Uwaga: .iss jest w "Installer/", więc do plików w ../dist i ../assets używamy ścieżek z "..\"
#define AppIcon "..\assets\logo.ico"
#define AppExe  "..\dist\CodePass.exe"
#define OutDir  "..\dist"

[Setup]
AppId={{BFCF9E5D-3C23-4E27-A89E-FF1122334455}}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
OutputDir={#OutDir}
OutputBaseFilename=CodePass_Installer
SetupIconFile={#AppIcon}
Compression=lzma
SolidCompression=yes
WizardStyle=modern
UninstallDisplayIcon={app}\{#MyAppExeName}
PrivilegesRequired=admin
ArchitecturesInstallIn64BitMode=x64
DisableDirPage=no
DisableProgramGroupPage=yes

[Languages]
Name: "polish"; MessagesFile: "compiler:Languages\Polish.isl"
Name: "english"; MessagesFile: "compiler:Default.isl"

[Files]
; plik EXE aplikacji
Source: "{#AppExe}"; DestDir: "{app}"; Flags: ignoreversion
; ikona (nieobowiązkowa, ale ładnie wygląda w odinstalatorze)
Source: "{#AppIcon}"; DestDir: "{app}"; Flags: ignoreversion

[Tasks]
Name: "desktopicon"; Description: "Utwórz ikonę na pulpicie"; GroupDescription: "Skróty:"

[Icons]
; skrót w menu Start
Name: "{autoprograms}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
; skrót na pulpicie (opcjonalny)
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
; uruchom aplikację po instalacji
Filename: "{app}\{#MyAppExeName}"; Description: "Uruchom CodePass"; Flags: nowait postinstall skipifsilent
