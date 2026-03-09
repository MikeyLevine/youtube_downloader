; setup.iss - Inno Setup installer script for YT Downloader

#define AppName      "YT Downloader"
#define AppVersion   "1.0.0"
#define AppExeName   "YTDownloader.exe"
#define SourceDir    "..\dist\YTDownloader"
#define AppIcon      "..\img\icon.ico"

[Setup]
AppId={{A1B2C3D4-E5F6-7890-ABCD-EF1234567890}
AppName={#AppName}
AppVersion={#AppVersion}
DefaultDirName={autopf}\{#AppName}
DefaultGroupName={#AppName}
AllowNoIcons=yes
OutputDir={#SourcePath}Output
OutputBaseFilename=YTDownloader_Setup
SetupIconFile={#AppIcon}
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=admin
MinVersion=10.0
ArchitecturesInstallIn64BitMode=x64compatible

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"

[Files]
Source: "..\dist\YTDownloader\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\{#AppName}"; Filename: "{app}\{#AppExeName}"; IconFilename: "{app}\{#AppExeName}"
Name: "{group}\Uninstall {#AppName}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\{#AppExeName}"; IconFilename: "{app}\{#AppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#AppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(AppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
Type: filesandordirs; Name: "{app}"

[Code]
function NodeJsInstalled(): Boolean;
var
  NodePath: String;
begin
  Result := RegQueryStringValue(HKLM, 'SOFTWARE\Node.js', 'InstallPath', NodePath)
         or RegQueryStringValue(HKCU, 'SOFTWARE\Node.js', 'InstallPath', NodePath);
  if not Result then
    Result := FileExists('C:\Program Files\nodejs\node.exe')
           or FileExists(ExpandConstant('{pf}\nodejs\node.exe'));
end;

procedure CurStepChanged(CurStep: TSetupStep);
begin
  if CurStep = ssPostInstall then
  begin
    if not NodeJsInstalled() then
    begin
      MsgBox(
        'YT Downloader installed successfully!' + #13#10 + #13#10 +
        'OPTIONAL: For 1080p/4K downloads, install Node.js from:' + #13#10 +
        'https://nodejs.org' + #13#10 + #13#10 +
        'Without Node.js, downloads are limited to 720p.',
        mbInformation, MB_OK
      );
    end;
  end;
end;
