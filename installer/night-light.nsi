Unicode true
RequestExecutionLevel user
SetCompressor zlib
Name "Night Light Early Access"
Caption "Night Light Early Access Setup"
BrandingText "Night Light by HT"
OutFile "${SETUP_OUTPUT}"
InstallDir "$LOCALAPPDATA\Programs\Night Light"
!include "MUI2.nsh"
!include "nsDialogs.nsh"
!include "x64.nsh"
!include "WinVer.nsh"
!include "${PAYLOAD_INCLUDE}"
; Unattended installs use the standard NSIS /S switch. Custom nsDialogs pages are
; never created in silent mode, so no IfSilent guards are needed here. Do not add
; a silent-mode override directive or /S stops working for scripted deployments.
!ifndef APP_VERSION
  !error "APP_VERSION must be defined by build_installer.py"
!endif
!define MUI_ICON "..\assets\app.ico"
!define MUI_UNICON "..\assets\app.ico"
Page custom WelcomePage
!insertmacro MUI_PAGE_INSTFILES
Page custom FinishPage
!insertmacro MUI_UNPAGE_CONFIRM
!insertmacro MUI_UNPAGE_INSTFILES
!insertmacro MUI_LANGUAGE "English"

Var PageDialog
Var PageLabel
Var HeadingFont

Function WelcomePage
  !insertmacro MUI_HEADER_TEXT "A calmer screen, ready when you are" "Night Light by HT - Early Access"
  nsDialogs::Create 1018
  Pop $PageDialog
  CreateFont $HeadingFont "Segoe UI" 15 600
  ${NSD_CreateLabel} 12u 8u 276u 24u "Welcome to Night Light"
  Pop $PageLabel
  SendMessage $PageLabel ${WM_SETFONT} $HeadingFont 1
  ${NSD_CreateLabel} 12u 38u 276u 26u "Adjust screen warmth yourself, or let Smart Mode ease you into the evening."
  Pop $PageLabel
  ${NSD_CreateLabel} 12u 68u 276u 26u "Unsigned Early Access: Windows cannot verify the publisher. Install only if you trust the download."
  Pop $PageLabel
  ${NSD_CreateLabel} 12u 98u 276u 40u "Setup updates recognized older versions and keeps your preferences. Night Light will close and restore normal screen colors. You choose when to open the app."
  Pop $PageLabel
  nsDialogs::Show
FunctionEnd

Function FinishPage
  !insertmacro MUI_HEADER_TEXT "Night Light is installed" "Your preferences are ready when you are."
  nsDialogs::Create 1018
  Pop $PageDialog
  ${NSD_CreateLabel} 12u 8u 276u 24u "You're ready to get started"
  Pop $PageLabel
  SendMessage $PageLabel ${WM_SETFONT} $HeadingFont 1
  ${NSD_CreateLabel} 12u 38u 276u 28u "1. Open Start and search for Night Light Controls. Choose Smart or Manual to get started."
  Pop $PageLabel
  ${NSD_CreateLabel} 12u 72u 276u 38u "2. Search Start for Night Light, right-click it and choose Pin to taskbar. Click the pinned moon to turn the filter on or off."
  Pop $PageLabel
  ${NSD_CreateLink} 12u 116u 276u 16u "Read the installation and getting-started guide"
  Pop $PageLabel
  ${NSD_OnClick} $PageLabel OpenGuide
  nsDialogs::Show
FunctionEnd

Function OpenGuide
  Pop $0
  ExecShell "open" "https://hasstechapi.com/night-light/install/"
FunctionEnd

Function .onInit
  SetShellVarContext current
  StrCpy $INSTDIR "$LOCALAPPDATA\Programs\Night Light"
  ${IfNot} ${RunningX64}
    MessageBox MB_ICONSTOP "This candidate requires Windows 11 on an x64 computer." /SD IDOK
    Abort
  ${EndIf}
  ${IfNot} ${AtLeastWin11}
    MessageBox MB_ICONSTOP "This candidate requires Windows 11." /SD IDOK
    Abort
  ${EndIf}
  System::Call 'kernel32::CreateMutexW(p 0, i 0, w "Local\HassTech.NightLight.Setup") p.r0'
  System::Call 'kernel32::GetLastError() i.r1'
  IntCmp $1 183 busy
  Goto check_runtime
busy:
  MessageBox MB_ICONSTOP "Another Night Light setup is open. Close it before continuing." /SD IDOK
  Abort
check_runtime:
  SetRegView 32
  ReadRegStr $0 HKLM "Software\Microsoft\EdgeUpdate\Clients\{F3017226-FE2A-4295-8BDF-00C3A9A7E4C5}" "pv"
  StrCmp $0 "" user_runtime
  StrCmp $0 "0.0.0.0" user_runtime ready
user_runtime:
  ReadRegStr $0 HKCU "Software\Microsoft\EdgeUpdate\Clients\{F3017226-FE2A-4295-8BDF-00C3A9A7E4C5}" "pv"
  StrCmp $0 "" missing_runtime
  StrCmp $0 "0.0.0.0" missing_runtime ready
missing_runtime:
  MessageBox MB_YESNO|MB_ICONINFORMATION "Night Light needs Microsoft Edge WebView2 Runtime. Setup will stop without changing your app.$\r$\n$\r$\nOpen Microsoft's official download page? You can also obtain its offline installer there." /SD IDNO IDNO stop_setup
  ExecShell "open" "https://developer.microsoft.com/en-us/microsoft-edge/webview2/#download-section"
stop_setup:
  Abort
ready:
FunctionEnd

Section "Install"
  InitPluginsDir
  ClearErrors
  !insertmacro PayloadFiles
  IfErrors install_failed
  SetOutPath "$PLUGINSDIR"
  File /oname=upgrade.ps1 "upgrade.ps1"
  File /oname=legacy-installations.json "legacy-installations.json"
  nsExec::ExecToLog '"$WINDIR\Sysnative\WindowsPowerShell\v1.0\powershell.exe" -NoProfile -NonInteractive -File "$PLUGINSDIR\upgrade.ps1" -IncomingRoot "$PLUGINSDIR\incoming" -ReceiptSha256 ${OWNERSHIP_SHA256}'
  Pop $0
  StrCmp $0 "0" replacement_done install_failed
replacement_done:
  WriteUninstaller "$INSTDIR\Uninstall.exe"
  IfErrors install_failed
  WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\HassTechNightLight" "DisplayName" "Night Light Early Access"
  WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\HassTechNightLight" "UninstallString" '"$INSTDIR\Uninstall.exe"'
  WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\HassTechNightLight" "InstallLocation" "$INSTDIR"
  WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\HassTechNightLight" "DisplayVersion" "${APP_VERSION}"
  WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\HassTechNightLight" "Publisher" "HassTech"
  WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\HassTechNightLight" "DisplayIcon" "$INSTDIR\app\NightLight.exe"
  WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\HassTechNightLight" "URLInfoAbout" "https://hasstechapi.com/night-light/"
  WriteRegDWORD HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\HassTechNightLight" "NoModify" 1
  WriteRegDWORD HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\HassTechNightLight" "NoRepair" 1
  Goto install_done
install_failed:
  SetErrorLevel 2
  MessageBox MB_ICONSTOP "Setup did not finish. No new app was started. Review NightLight-setup-error.txt in your local application-data folder for details. Your preferences were retained." /SD IDOK
  Abort
install_done:
SectionEnd

Section "Uninstall"
  SetShellVarContext current
  StrCpy $INSTDIR "$LOCALAPPDATA\Programs\Night Light"
  InitPluginsDir
  SetOutPath "$PLUGINSDIR"
  File /oname=remove-owned.ps1 "remove-owned.ps1"
  nsExec::ExecToLog '"$WINDIR\Sysnative\WindowsPowerShell\v1.0\powershell.exe" -NoProfile -NonInteractive -File "$PLUGINSDIR\remove-owned.ps1" -ReceiptSha256 ${OWNERSHIP_SHA256}'
  Pop $0
  StrCmp $0 "0" removed
  MessageBox MB_ICONSTOP "Removal could not be completed. Close Night Light and review the setup log. Changed or unrecognized files and your preferences are preserved." /SD IDOK
  Abort
removed:
  ReadRegStr $0 HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\HassTechNightLight" "InstallLocation"
  StrCmp $0 "$INSTDIR" 0 keep_registration
  DeleteRegKey HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\HassTechNightLight"
keep_registration:
  Delete "$INSTDIR\Uninstall.exe"
  ; Nonrecursive directory removal preserves unknown files and directories.
  RMDir "$INSTDIR\app\THIRD-PARTY-LICENSES"
  RMDir "$INSTDIR\app"
  RMDir "$INSTDIR"
  DetailPrint "Verified app files removed. Preferences, backups, WebView2 and unknown files were retained."
SectionEnd
