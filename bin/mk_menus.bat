@setlocal enableextensions enabledelayedexpansion
@echo off

REM Menu installation needs to be always done with the root python for sake
REM    of correct menu grouping

set "PYTHON=%~dp0..\pythonw.exe"
set "SCRIPT=install_menu.py"
set "PREFIX=%~1"
set "MENU_FILE=%~2"
if "%~3" == "REMOVE" (set REMOVE=1) else (set REMOVE=0)

echo import sys > "%SCRIPT%"
echo import os >> "%SCRIPT%"
echo from os.path import abspath, basename, join >> "%SCRIPT%"
echo import menuinst >> "%SCRIPT%"
echo prefix = r"%%s" %% "%PREFIX%" >> "%SCRIPT%"
echo env_name = (None if abspath(prefix) == abspath(sys.prefix) else >> "%SCRIPT%"
echo     basename(prefix)) >> "%SCRIPT%"
echo env_setup_cmd = ('activate "%%s"' %% env_name) if env_name else None >> "%SCRIPT%"
echo menuinst.install(join(prefix, "%MENU_FILE%"), int("%REMOVE%"), root_prefix=sys.prefix, >> "%SCRIPT%"
echo         target_prefix=prefix, env_name=env_name, env_setup_cmd=env_setup_cmd) >> "%SCRIPT%"

:: User-level install
if EXIST "%PREFIX%\.nonadmin" call :install_user_menu "%PYTHON%" "%SCRIPT%" & goto finish
call :install_system_menu "%PYTHON%" "%SCRIPT%" & goto finish

:install_user_menu
    set "PYTHON=%~1"
    set "SCRIPT=%~2"
    "%PYTHON%" "%SCRIPT%"
    del "%SCRIPT%"
    goto :eof

:install_system_menu
    REM http://stackoverflow.com/questions/4051883/batch-script-how-to-check-for-admin-rights
    REM Quick test for Windows generation: UAC aware or not ; all OS before NT4 ignored for simplicity
    SET NewOSWith_UAC=YES
    VER | FINDSTR /IL "5." > NUL
    IF %ERRORLEVEL% == 0 SET NewOSWith_UAC=NO
    VER | FINDSTR /IL "4." > NUL
    IF %ERRORLEVEL% == 0 SET NewOSWith_UAC=NO

    set "PYTHON=%~1"
    set "SCRIPT=%~2"

    REM Test if Admin
    CALL NET SESSION >nul 2>&1
    IF NOT %ERRORLEVEL% == 0 (

    if /i "%NewOSWith_UAC%"=="YES" (
    echo Set UAC = CreateObject^("Shell.Application"^) > "%temp%\getadmin.vbs"
    echo UAC.ShellExecute "%PYTHON%", "%SCRIPT%", "", "runas", 1 >> "%temp%\getadmin.vbs"
    "%SystemRoot%\System32\WScript.exe" "%temp%\getadmin.vbs"
    del "%temp%\getadmin.vbs"
    )
    ) else (
    REM   Already elevated.  Just run the script.
    "%PYTHON%" "%SCRIPT%"
    )

    del "%SCRIPT%"
    goto :eof

:finish

:END
endlocal
