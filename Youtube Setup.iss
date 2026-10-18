; YouTube İndirici — Inno Setup Script

#define MyAppName "YouTube İndirici"
#define MyAppVersion "1.2.4"
#define MyAppPublisher "IzzmooPro"
#define MyAppURL "https://github.com/IzzmooPro/ytdownloader"
#define MyAppExeName "YouTube Indirici.exe"
#define MyAppIcon AddBackslash(SourcePath) + "icon.ico"
#define MyAppExePath AddBackslash(SourcePath) + "dist\\YouTube Indirici.exe"

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
OutputDir={#SourcePath}
OutputBaseFilename=YouTube İndirici Setup v{#MyAppVersion}
SetupIconFile={#MyAppIcon}
SolidCompression=yes
WizardStyle=modern
CloseApplications=yes
CloseApplicationsFilter=*.exe
; Uygulamanın tek-instance mutex'i — kurulum sırasında uygulama açıksa
; Inno kullanıcıya kibarca "kapatın" uyarısı gösterir (taskkill'e ek güvence)
AppMutex=YTDownloader_SingleInstance_v1

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

[CustomMessages]
english.RemoveUserData=Do you also want to delete settings, download history and the embedded FFmpeg?%n(%s)
turkish.RemoveUserData=Ayarlar, indirme geçmişi ve gömülü FFmpeg de silinsin mi?%n(%s)

[Code]
function InitializeSetup(): Boolean;
var
  ResultCode: Integer;
  WaitPid: String;
begin
  // Uygulama içi güncelleme /WAITPID=<pid> verir: program kuyruğu diske yazıp
  // kendisi kapanana kadar bekle. Kapanmazsa (kullanıcı vazgeçti) kurma.
  WaitPid := ExpandConstant('{param:WAITPID|}');
  if WaitPid <> '' then
  begin
    Exec('powershell.exe',
      '-NoProfile -NonInteractive -Command "Wait-Process -Id ' + WaitPid +
      ' -Timeout 300 -ErrorAction SilentlyContinue; if (Get-Process -Id ' + WaitPid +
      ' -ErrorAction SilentlyContinue) { exit 1 }"',
      '', SW_HIDE, ewWaitUntilTerminated, ResultCode);
    if ResultCode <> 0 then
    begin
      Log('Program kapanmadı, güncelleme iptal edildi');
      Result := False;
      exit;
    end;
  end;
  Exec('taskkill.exe', '/F /IM "{#MyAppExeName}"', '', SW_HIDE, ewWaitUntilTerminated, ResultCode);
  Sleep(1200);
  Result := True;
end;

// Kaldırma sonunda kullanıcı verisini SORARAK temizle — sessizce silme.
// %APPDATA%\MyYouTubeDownloader: ayarlar, geçmiş, loglar, ffmpeg (~150 MB)
procedure CurUninstallStepChanged(CurUninstallStep: TUninstallStep);
var
  DataDir: String;
begin
  if CurUninstallStep = usPostUninstall then
  begin
    DataDir := ExpandConstant('{userappdata}\MyYouTubeDownloader');
    if DirExists(DataDir) then
    begin
      if MsgBox(FmtMessage(CustomMessage('RemoveUserData'), [DataDir]),
                mbConfirmation, MB_YESNO) = IDYES then
        DelTree(DataDir, True, True, True);
    end;
  end;
end;

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent
; Uygulama içi güncelleme sessiz kurulum yapar (/SILENT) — bitince programı
; yeniden aç. runasoriginaluser: kurulum yönetici olarak çalışsa da program
; normal kullanıcı yetkisiyle açılır (yönetici olarak açılırsa tarayıcıdan
; sürükle-bırak gibi özellikler Windows tarafından engellenir).
Filename: "{app}\{#MyAppExeName}"; Flags: nowait runasoriginaluser; Check: WizardSilent
