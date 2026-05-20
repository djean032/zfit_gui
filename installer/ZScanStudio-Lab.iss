[Setup]
AppId={{7A562867-9952-43E3-8D54-3942CD4CA295}
AppName=ZScan Studio (Lab)
AppVersion=0.1.0
AppPublisher=ZScan Studio
DefaultDirName={autopf}\ZScan Studio
DefaultGroupName=ZScan Studio
DisableProgramGroupPage=yes
OutputDir=..\dist\installers
OutputBaseFilename=ZScanStudio-Lab-Setup
Compression=lzma
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=admin
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
UninstallDisplayIcon={app}\ZScanStudio-Lab.exe

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; GroupDescription: "Additional shortcuts:"; Flags: unchecked

[Files]
Source: "..\dist\ZScanStudio-Lab\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{autoprograms}\ZScan Studio\ZScan Studio (Lab)"; Filename: "{app}\ZScanStudio-Lab.exe"
Name: "{autodesktop}\ZScan Studio (Lab)"; Filename: "{app}\ZScanStudio-Lab.exe"; Tasks: desktopicon

[Run]
Filename: "{app}\ZScanStudio-Lab.exe"; Description: "Launch ZScan Studio (Lab)"; Flags: nowait postinstall skipifsilent
