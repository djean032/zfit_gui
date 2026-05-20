[Setup]
AppId={{7AC6A6D1-49E4-428C-B7FF-0EA34A0452DF}
AppName=ZScan Studio (Standard)
AppVersion=0.1.0
AppPublisher=ZScan Studio
DefaultDirName={autopf}\ZScan Studio
DefaultGroupName=ZScan Studio
DisableProgramGroupPage=yes
OutputDir=..\dist\installers
OutputBaseFilename=ZScanStudio-Standard-Setup
Compression=lzma
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=admin
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
UninstallDisplayIcon={app}\ZScanStudio-Standard.exe

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; GroupDescription: "Additional shortcuts:"; Flags: unchecked

[Files]
Source: "..\dist\ZScanStudio-Standard\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{autoprograms}\ZScan Studio\ZScan Studio (Standard)"; Filename: "{app}\ZScanStudio-Standard.exe"
Name: "{autodesktop}\ZScan Studio (Standard)"; Filename: "{app}\ZScanStudio-Standard.exe"; Tasks: desktopicon

[Run]
Filename: "{app}\ZScanStudio-Standard.exe"; Description: "Launch ZScan Studio (Standard)"; Flags: nowait postinstall skipifsilent
