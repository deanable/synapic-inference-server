; Inno Setup definition for the Synapic inference server.
; APP_VERSION should be a numeric dotted version such as 1.2.3.

#define AppVersionFromEnvironment GetEnv("APP_VERSION")
#if AppVersionFromEnvironment == ""
#define AppVersion "0.1.0"
#else
#define AppVersion AppVersionFromEnvironment
#endif

[Setup]
AppId={{F65A1C48-4B74-4B7F-9B46-3F1D0E4A4C3E}}
AppName=Synapic Inference Server
AppVersion={#AppVersion}
AppPublisher=Synapic
DefaultDirName={autopf}\Synapic Inference Server
DefaultGroupName=Synapic Inference Server
OutputDir=..\dist
OutputBaseFilename=synapic-inference-installer
Compression=lzma
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=admin
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
DisableProgramGroupPage=yes
Uninstallable=yes

[Files]
Source: "..\dist\synapic-inference.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\.env.example"; DestDir: "{app}"; DestName: ".env.example"; Flags: ignoreversion
Source: "..\README.md"; DestDir: "{app}"; Flags: isreadme

[Icons]
Name: "{group}\Synapic Inference Server"; Filename: "{app}\synapic-inference.exe"; WorkingDir: "{app}"
