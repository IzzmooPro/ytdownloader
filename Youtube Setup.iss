; YouTube İndirici — Inno Setup Script

#define MyAppName "YouTube İndirici"
#define MyAppVersion "v1.0.0"
#define MyAppPublisher "IzzmooPro"
#define MyAppURL "IzzmooPro@gmail.com"
#define MyAppExeName "YouTube Indirici.exe"
#define MyAppIcon "C:\Users\Universe\Desktop\Programlar TEST\2026 YENİLER\Youtube Downloader\icon.ico"
#define MyAppExePath "C:\Users\Universe\Desktop\Programlar TEST\2026 YENİLER\Youtube Downloader\dist\YouTube Indirici.exe"
#define MyAppDir "C:\Users\Universe\Desktop\Programlar TEST\2026 YENİLER\Youtube Downloader"

[Setup]
AppId={{2055CFB7-316F-4F25-A557-7CC8C93497AE}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}
DefaultDirName={autopf}\{#MyAppName}
UninstallDisplayIcon={app}\{#MyAppExeName}
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
DisableProgramGroupPage=yes
OutputDir=C:\Users\Universe\Desktop
OutputBaseFilename=YouTube İndirici Setup
SetupIconFile={#MyAppIcon}
SolidCompression=yes
WizardStyle=modern

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"
Name: "turkish"; MessagesFile: "compiler:Languages\Turkish.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
Source: "{#MyAppExePath}"; DestDir: "{app}"; DestName: "{#MyAppExeName}"; Flags: ignoreversion

[Icons]
Name: "{autoprograms}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; IconFilename: "{app}\{#MyAppExeName}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; IconFilename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent
