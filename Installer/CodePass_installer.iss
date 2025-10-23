; ==========================================================
; CodePass — Online Installer PRO
; (C) 2025 CodePass Software
; ==========================================================

#define MyAppName "CodePass"
#define MyAppPublisher "CodePass Software"
#define MyAppExeName "CodePass.exe"
#define MyAppURL "https://github.com/codepass0v12/Codepass"
#define MyAppVersion "2.0.6"

[Setup]
AppId={{C0D3-PA55-1234-5678-ABCDEF000001}}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
OutputDir=..\dist
OutputBaseFilename=CodePass_Online_Installer
Compression=lzma
SolidCompression=yes
SetupIconFile=..\assets\logo.ico
WizardStyle=modern
LicenseFile=LICENSE.txt
PrivilegesRequired=admin
DisableProgramGroupPage=yes
UninstallDisplayIcon={app}\{#MyAppExeName}
UninstallDisplayName={#MyAppName}

[Languages]
Name: "polish"; MessagesFile: "compiler:Languages\Polish.isl"

[Tasks]
Name: "desktopicon"; Description: "Utwórz ikonę na pulpicie"; GroupDescription: "Dodatkowe zadania"; Flags: unchecked
Name: "autoupdate"; Description: "Sprawdź aktualizacje po instalacji"; GroupDescription: "Dodatkowe zadania"; Flags: unchecked

[Files]
Source: "..\assets\logo.ico"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\public_key.pem"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\installer\downloader.ps1"; DestDir: "{tmp}"; Flags: deleteafterinstall
Source: "..\installer\LICENSE.txt"; DestDir: "{app}"; Flags: ignoreversion

[Dirs]
Name: "{userappdata}\CodePass"; Flags: uninsalwaysuninstall

[Icons]
; Menu Start
Name: "{autoprograms}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
; Skrót na pulpicie (jeśli użytkownik zaznaczy)
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
; 1️⃣ Pobiera i instaluje najnowszą wersję z GitHuba
Filename: "powershell"; \
  Parameters: "-ExecutionPolicy Bypass -File ""{tmp}\downloader.ps1"" -installDir ""{app}"""; \
  Flags: runhidden waituntilterminated
; 2️⃣ Uruchamia CodePass po instalacji
Filename: "{app}\{#MyAppExeName}"; Description: "Uruchom CodePass po instalacji"; Flags: nowait postinstall skipifsilent
; 3️⃣ Opcjonalnie sprawdza aktualizacje
Filename: "{app}\{#MyAppExeName}"; Description: "Sprawdź aktualizacje po instalacji"; Flags: postinstall skipifsilent; Tasks: autoupdate

[UninstallDelete]
Type: files; Name: "{app}\update.json"
Type: files; Name: "{app}\update_*.zip"
Type: files; Name: "{app}\update_*.sig"
Type: dirifempty; Name: "{userappdata}\CodePass"

[Code]
var
  UserDataDirPage: TInputDirWizardPage;

function InitializeSetup(): Boolean;
var
  ResultCode: Integer;
begin
  if DirExists(ExpandConstant('{app}')) then begin
    MsgBox('Wykryto istniejącą instalację CodePass. Stara wersja zostanie odinstalowana.', mbInformation, MB_OK);
    Exec(ExpandConstant('{uninstallexe}'), '/VERYSILENT', '', SW_SHOW, ewWaitUntilTerminated, ResultCode);
  end;
  Result := True;
end;

procedure InitializeWizard;
begin
  UserDataDirPage := CreateInputDirPage(
    wpSelectDir,
    'Folder danych użytkownika',
    'Wybierz, gdzie CodePass ma przechowywać dane użytkownika.',
    'Zalecane jest pozostawienie domyślnego folderu AppData.',
    False, ''
  );
  UserDataDirPage.Add('');
  UserDataDirPage.Values[0] := ExpandConstant('{userappdata}\CodePass');
end;

procedure CurStepChanged(CurStep: TSetupStep);
var
  DataDir: string;
begin
  if CurStep = ssPostInstall then begin
    DataDir := UserDataDirPage.Values[0];
    if not DirExists(DataDir) then
      ForceDirectories(DataDir);
    SaveStringToFile(ExpandConstant('{app}\userdata_path.txt'), DataDir, False);
  end;
end;
