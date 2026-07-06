#define AppName "PDF to DXF"
#define AppExeName "PDF-to-DXF-Desktop"
#define AppDirName "PDF-to-DXF"
#define AppPublisher "Taam4142"
#define AppRepositoryUrl "https://github.com/Taam4142/PDF-to-DXF"
#define RepoRoot AddBackslash(SourcePath) + "..\"

#ifndef AppVersion
#define AppVersion "0.1.0"
#endif

[Setup]
AppId={{F7E8218E-7F0A-4B1C-B6F9-C6D90185724F}
AppName={#AppName}
AppVersion={#AppVersion}
AppPublisher={#AppPublisher}
AppPublisherURL={#AppRepositoryUrl}
AppSupportURL={#AppRepositoryUrl}/issues
AppUpdatesURL={#AppRepositoryUrl}/releases
DefaultDirName={localappdata}\Programs\{#AppDirName}
DefaultGroupName={#AppName}
DisableProgramGroupPage=yes
OutputDir={#RepoRoot}dist\installer
OutputBaseFilename={#AppExeName}-Setup-{#AppVersion}
SetupIconFile={#RepoRoot}assets\app_icon.ico
UninstallDisplayIcon={app}\{#AppExeName}.exe
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=lowest
ArchitecturesAllowed=x64
ArchitecturesInstallIn64BitMode=x64
VersionInfoVersion={#AppVersion}
VersionInfoCompany={#AppPublisher}
VersionInfoDescription=Installer for {#AppName}
VersionInfoProductName={#AppName}
VersionInfoProductVersion={#AppVersion}

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
Source: "{#RepoRoot}dist\windows-native-app\{#AppExeName}.exe"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{autoprograms}\{#AppName}"; Filename: "{app}\{#AppExeName}.exe"; WorkingDir: "{app}"
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\{#AppExeName}.exe"; WorkingDir: "{app}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#AppExeName}.exe"; Description: "{cm:LaunchProgram,{#AppName}}"; Flags: nowait postinstall skipifsilent
