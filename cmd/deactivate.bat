@echo off
setlocal

if not "%1" == "--help" goto skipusage
    (
    echo Usage: deactivate
    echo.
    echo Deactivates previously activated Conda
    echo environment.
    echo.
    echo Additional arguments are ignored.
    ) 1>&2
    exit /b 1
:skipusage

REM Deactivate a previous activation if it is live
IF NOT "%CONDA_PATH_BACKUP%" == "" (SET "PATH=%CONDA_PATH_BACKUP%" && SET "CONDA_PATH_BACKUP=")
IF NOT "%CONDA_OLD_PS1%" == "" (SET "PROMPT=%CONDA_OLD_PS1%" && SET "CONDA_OLD_PS1=")

endlocal & (
            set "CONDA_DEFAULT_ENV="
            set "PATH=%PATH%"
            set "PROMPT=%PROMPT%"
           )
