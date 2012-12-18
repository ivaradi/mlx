; NSIS installer script for MAVA Logger X

;--------------------------------
;Include Modern UI

  !include "MUI.nsh"
  !include "nsDialogs.nsh"
  !include "TextFunc.nsh"
  !include "mlx-common.nsh"

;--------------------------------
;General

  Var ApplicationName

  Function .onInit
    StrCpy $ApplicationName "Mava Logger X"
  FunctionEnd

  ;Name and file
  Name "MAVA Logger X"
  Caption "MAVA Logger X ${MLX_VERSION} Setup"
  OutFile "MAVA Logger X-${MLX_VERSION}-Setup.exe"

  ;Default installation folder
  InstallDir "$PROGRAMFILES\MAVA Logger X"

  ;Vista redirects $SMPROGRAMS to all users without this
  RequestExecutionLevel admin

;--------------------------------
;Variables

  Var MUI_TEMP
  Var STARTMENU_FOLDER
  Var Variable
  Var Secondary
  Var Secondary_State
  Var LinkName
  Var Parameters

;--------------------------------
;Interface Settings

  !define MUI_ICON "logo.ico"
  !define MUI_UNICON "logo_uninst.ico"
  !define MUI_ABORTWARNING

;--------------------------------
;Pages

  !insertmacro MUI_PAGE_LICENSE "license.txt"
  Page custom optionsPage ;optionsPageLeave
  !insertmacro MUI_PAGE_COMPONENTS
  !insertmacro MUI_PAGE_DIRECTORY

  ;Start Menu Folder Page Configuration
  ;!define MUI_STARTMENUPAGE_REGISTRY_ROOT "HKCU"
  ;!define MUI_STARTMENUPAGE_REGISTRY_KEY "Software\MAVA Logger X"
  ;!define MUI_STARTMENUPAGE_REGISTRY_VALUENAME "Start Menu Folder"

  !insertmacro MUI_PAGE_STARTMENU Application $STARTMENU_FOLDER

  !insertmacro MUI_PAGE_INSTFILES

  !insertmacro MUI_UNPAGE_CONFIRM
  !insertmacro MUI_UNPAGE_INSTFILES

  Function optionsPage
     !insertmacro MUI_HEADER_TEXT $(InstallOpts_Title) $(InstallOpts_SubTitle)

     nsDialogs::Create 1018
     Pop $Variable

     ${If} $Variable == error
         Abort
     ${Endif}

     ${NSD_CreateLabel} 0 0 100% 32u $(InstallOpts_SecondaryExpl)
     Pop $Variable

     ${NSD_CreateCheckBox} 12 62 100% 12u $(InstallOpts_Secondary)
     Pop $Secondary
     ${NSD_SetState} $Secondary $Secondary_State
     GetFunctionAddress $Variable onSecondaryClicked
     nsDialogs::onClick $Secondary $Variable

     nsDialogs::Show
  FunctionEnd

  Function onSecondaryClicked
     Pop $Secondary
     ${NSD_GetState} $Secondary $Secondary_State
     ${If} $Secondary_State == ${BST_CHECKED}
         StrCpy $INSTDIR "$PROGRAMFILES\MAVA Logger X (Secondary)"
         StrCpy $STARTMENU_FOLDER "MAVA Logger X (Secondary)"
     ${Else}
         StrCpy $INSTDIR "$PROGRAMFILES\MAVA Logger X"
         StrCpy $STARTMENU_FOLDER "MAVA Logger X"
     ${EndIf}
  FunctionEnd

;--------------------------------
;Languages

  !insertmacro MUI_LANGUAGE "English"
  !insertmacro MUI_LANGUAGE "Hungarian"

;--------------------------------
;Installer Sections

Section "MAVA Logger X" SecMLX

  SetOutPath "$INSTDIR"

  ${If} $Secondary_State == ${BST_CHECKED}
    StrCpy $LinkName "MAVA Logger X (Secondary)"
    StrCpy $Parameters "secondary"
  ${Else}
    StrCpy $LinkName "MAVA Logger X"
    StrCpy $Parameters ""
  ${EndIf}

  ;ADD YOUR OWN FILES HERE...
  File /r dist\*.*

  ;Create the uninstaller config file
  ${ConfigWrite} "$INSTDIR\Uninstall.conf" "StartMenuFolder=" "$STARTMENU_FOLDER" $Variable
  ${ConfigWrite} "$INSTDIR\Uninstall.conf" "LinkName=" "$LinkName" $Variable

  ;Create uninstaller

  WriteUninstaller "$INSTDIR\Uninstall.exe"

  !insertmacro MUI_STARTMENU_WRITE_BEGIN Application
    ;Create shortcuts
    CreateDirectory "$SMPROGRAMS\$STARTMENU_FOLDER"
    CreateShortCut "$SMPROGRAMS\$STARTMENU_FOLDER\MAVA Logger X.lnk" "$INSTDIR\runmlx.exe" "$Parameters"
    CreateShortCut "$SMPROGRAMS\$STARTMENU_FOLDER\Uninstall.lnk" "$INSTDIR\Uninstall.exe"
    CreateShortCut "$DESKTOP\$LinkName.lnk" "$INSTDIR\runmlx.exe" "$Parameters"
  !insertmacro MUI_STARTMENU_WRITE_END
SectionEnd

;--------------------------------
;Descriptions

  ;Language strings
  LangString DESC_SecMLX ${LANG_ENGLISH} "The MAVA Logger X application itself."
  LangString DESC_SecMLX ${LANG_HUNGARIAN} "Maga a MAVA Logger X alkalmazás."

  ;Assign language strings to sections
  !insertmacro MUI_FUNCTION_DESCRIPTION_BEGIN
    !insertmacro MUI_DESCRIPTION_TEXT ${SecMLX} $(DESC_SecMLX)
  !insertmacro MUI_FUNCTION_DESCRIPTION_END

  LangString InstallOpts_Title ${LANG_ENGLISH} "Installation Options"
  LangString InstallOpts_Title ${LANG_HUNGARIAN} "Telepítési beállítások"

  LangString InstallOpts_SubTitle ${LANG_ENGLISH} "Choose the options for the installation"
  LangString InstallOpts_SubTitle ${LANG_HUNGARIAN} "Válassza ki a telepítés beállításait"

  LangString InstallOpts_SecondaryExpl ${LANG_ENGLISH} "If you select the option below, the program will be installed in a way that it can be used besides another, already existing installation. Its default configuration will be such that it does not conflict with another logger running as a primary one. Normally, you should leave this unchecked."
  LangString InstallOpts_SecondaryExpl ${LANG_HUNGARIAN} "Az alábbi opció kijelölésével a programot úgy fogjuk telepíteni, hogy azt egy másik mellett, azzal egyidejûen lehessen használni. Az alapértelmezett konfigurációja elkerüli a másik futó loggerrel való ütközést. Általában azonban ezt az opciót nem kell kijelölni."

  LangString InstallOpts_Secondary ${LANG_ENGLISH} "Install as a secondary copy"
  LangString InstallOpts_Secondary ${LANG_HUNGARIAN} "Telepítés másodlagos példányként"

;--------------------------------
;Uninstaller Section

Section "Uninstall"

  ;Read the uninstaller config file
  ${ConfigRead} "$INSTDIR\Uninstall.conf" "StartMenuFolder=" $MUI_TEMP
  ${ConfigRead} "$INSTDIR\Uninstall.conf" "LinkName=" $LinkName

  RMDir /r "$INSTDIR"

  Delete "$DESKTOP\$LinkName.lnk"
  Delete "$SMPROGRAMS\$MUI_TEMP\MAVA Logger X.lnk"
  Delete "$SMPROGRAMS\$MUI_TEMP\Uninstall.lnk"

  ;Delete empty start menu parent diretories
  StrCpy $MUI_TEMP "$SMPROGRAMS\$MUI_TEMP"

  startMenuDeleteLoop:
    ClearErrors
    RMDir $MUI_TEMP
    GetFullPathName $MUI_TEMP "$MUI_TEMP\.."

    IfErrors startMenuDeleteLoopDone

    StrCmp $MUI_TEMP $SMPROGRAMS startMenuDeleteLoopDone startMenuDeleteLoop
  startMenuDeleteLoopDone:
SectionEnd
