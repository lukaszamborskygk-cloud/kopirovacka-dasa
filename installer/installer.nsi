; Kopirovacka Installer Script (NSIS)
; Compile with: makensis installer.nsi

!define APP_NAME "Kopírovačka"
!define APP_NAME_SAFE "Kopirovacka"
!define APP_VERSION "1.0.0"
!define APP_EXE "Kopirovacka.exe"
!define INSTALL_DIR "$LOCALAPPDATA\Kopirovacka"
!define UNINSTALL_REG "Software\Microsoft\Windows\CurrentVersion\Uninstall\Kopirovacka"

; ── General ──────────────────────────────────────────────────────────
Name "${APP_NAME}"
OutFile "Kopirovacka_Installer.exe"
InstallDir "${INSTALL_DIR}"
RequestExecutionLevel user
Unicode True
SetCompressor /SOLID lzma

; ── MUI Settings ─────────────────────────────────────────────────────
!include "MUI2.nsh"
!include "LogicLib.nsh"

!define MUI_ABORTWARNING
!define MUI_BGCOLOR "1E1E2E"
!define MUI_TEXTCOLOR "E2E8F0"

; ── Pages ─────────────────────────────────────────────────────────────
Page custom WelcomePage WelcomeLeave

Function WelcomePage
    nsDialogs::Create 1018
    Pop $0
    ${If} $0 == error
        Abort
    ${EndIf}

    ; Background
    GetDlgItem $1 $HWNDPARENT 1
    SetCtlColors $1 "E2E8F0" "7C3AED"

    ; Title label
    ${NSD_CreateLabel} 20u 20u 260u 20u "${APP_NAME}"
    Pop $2
    CreateFont $R0 "Segoe UI" 16 700
    SendMessage $2 ${WM_SETFONT} $R0 1

    ; Subtitle
    ${NSD_CreateLabel} 20u 50u 260u 14u "Správca histórie schránky pre Windows"
    Pop $3
    CreateFont $R1 "Segoe UI" 10 400
    SendMessage $3 ${WM_SETFONT} $R1 1

    ; Divider info
    ${NSD_CreateLabel} 20u 80u 260u 60u "Aplikácia bude nainštalovaná do:$\r$\n${INSTALL_DIR}"
    Pop $4
    SendMessage $4 ${WM_SETFONT} $R1 1

    ; Desktop shortcut checkbox (checked by default)
    ${NSD_CreateCheckbox} 20u 155u 260u 14u "Vytvoriť skratku na pracovnej ploche"
    Pop $5
    ${NSD_Check} $5
    StrCpy $9 $5  ; save handle

    nsDialogs::Show
FunctionEnd

Function WelcomeLeave
    ${NSD_GetState} $9 $R9   ; $R9 = 1 if checked
FunctionEnd

; ── Install section ───────────────────────────────────────────────────
Section "Install"
    SetOutPath "${INSTALL_DIR}"

    ; Download / copy the exe
    File "dist\Kopirovacka.exe"

    ; Write uninstaller
    WriteUninstaller "${INSTALL_DIR}\Uninstall_Kopirovacka.exe"

    ; Registry for Add/Remove Programs
    WriteRegStr HKCU "${UNINSTALL_REG}" "DisplayName" "${APP_NAME}"
    WriteRegStr HKCU "${UNINSTALL_REG}" "DisplayVersion" "${APP_VERSION}"
    WriteRegStr HKCU "${UNINSTALL_REG}" "UninstallString" "${INSTALL_DIR}\Uninstall_Kopirovacka.exe"
    WriteRegStr HKCU "${UNINSTALL_REG}" "InstallLocation" "${INSTALL_DIR}"
    WriteRegDWORD HKCU "${UNINSTALL_REG}" "NoModify" 1
    WriteRegDWORD HKCU "${UNINSTALL_REG}" "NoRepair" 1

    ; Start Menu shortcut
    CreateDirectory "$SMPROGRAMS\Kopirovacka"
    CreateShortcut "$SMPROGRAMS\Kopirovacka\${APP_NAME}.lnk" \
        "${INSTALL_DIR}\${APP_EXE}"
    CreateShortcut "$SMPROGRAMS\Kopirovacka\Odinštalovať.lnk" \
        "${INSTALL_DIR}\Uninstall_Kopirovacka.exe"

    ; Desktop shortcut (if checkbox was checked)
    ${If} $R9 == 1
        CreateShortcut "$DESKTOP\${APP_NAME}.lnk" "${INSTALL_DIR}\${APP_EXE}"
    ${EndIf}

    ; Autostart with Windows (optional registry key)
    WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Run" \
        "Kopirovacka" '"${INSTALL_DIR}\${APP_EXE}"'

SectionEnd

; ── Uninstall section ──────────────────────────────────────────────────
Section "Uninstall"
    Delete "${INSTALL_DIR}\${APP_EXE}"
    Delete "${INSTALL_DIR}\Uninstall_Kopirovacka.exe"
    RMDir "${INSTALL_DIR}"

    Delete "$DESKTOP\${APP_NAME}.lnk"
    Delete "$SMPROGRAMS\Kopirovacka\${APP_NAME}.lnk"
    Delete "$SMPROGRAMS\Kopirovacka\Odinštalovať.lnk"
    RMDir "$SMPROGRAMS\Kopirovacka"

    DeleteRegKey HKCU "${UNINSTALL_REG}"
    DeleteRegValue HKCU "Software\Microsoft\Windows\CurrentVersion\Run" "Kopirovacka"

    ; Keep user data (history.db) unless they want full removal
    MessageBox MB_YESNO "Odstrániť aj históriu kopírovania (databázu)?" IDNO skip_data
        RMDir /r "$APPDATA\Kopirovacka"
    skip_data:

    MessageBox MB_OK "${APP_NAME} bol úspešne odinštalovaný."
SectionEnd
