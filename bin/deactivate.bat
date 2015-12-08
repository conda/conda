@echo off
SETLOCAL ENABLEDELAYEDEXPANSION

IF "%1" == "" GOTO skipmissingarg
    ECHO Usage: deactivate
    ECHO.
    ECHO Deactivates previously activated Conda
    ECHO environment.
    EXIT /b 1
:skipmissingarg

IF "%CONDA_DEFAULT_ENV%"=="" (
    REM special case for root env:
    REM   Checks for Library\bin on PATH.  If exists, we have root env on PATH.
    call :NORMALIZEPATH ROOT_PATH "%~dp0.."
    CALL SET "PATH_NO_ROOT=%%PATH:%ROOT_PATH%;=%%"
    IF NOT "%PATH_NO_ROOT%"=="%PATH%" SET "CONDA_DEFAULT_ENV=%ROOT_PATH%"
)

SET "SCRIPT_PATH=%~dp0"
IF "%SCRIPT_PATH:~-1%"=="\" SET "SCRIPT_PATH=%SCRIPT_PATH:~0,-1%"

REM Deactivate a previous activation if it is live
IF "%CONDA_PATH_BACKUP%" == "" GOTO skipdeactivate
    REM This search/replace removes the previous env from the path
    ECHO Deactivating environment "%CONDA_DEFAULT_ENV%"...

    REM Run any deactivate scripts
    IF NOT EXIST "%CONDA_DEFAULT_ENV%\etc\conda\deactivate.d" GOTO nodeactivate
        PUSHD "%CONDA_DEFAULT_ENV%\etc\conda\deactivate.d"
        FOR %%g IN (*.bat) DO CALL "%%g"
        POPD
    :nodeactivate

    REM Remove env name from PROMPT
    FOR /F "tokens=* delims=\" %%i IN ("%CONDA_DEFAULT_ENV%") DO SET "CONDA_OLD_ENV_NAME=%%~ni"
    CALL SET PROMPT=%%PROMPT:[%CONDA_OLD_ENV_NAME%] =%%

    REM CONDA_PATH_BACKUP is set in activate.bat
    CALL SET "PATH=%CONDA_PATH_BACKUP%"
:skipdeactivate

REM Make sure that root's Scripts dir is on PATH, for sake of keeping activate/deactivate available.
CALL SET "PATH_NO_SCRIPTS=%%PATH:%SCRIPT_PATH%=%%"
IF "%PATH_NO_SCRIPTS%"=="%PATH%" SET "PATH=%PATH%;%SCRIPT_PATH%"

REM Trim trailing semicolon, if any
IF "%PATH:~-1%"==";" SET "PATH=%PATH:~0,-1%"

REM Clean up any double colons we may have ended up with
SET "PATH=%PATH:;;=;%"

ENDLOCAL & (
    SET "PATH=%PATH%"
    SET "PROMPT=%PROMPT%"
    SET CONDA_DEFAULT_ENV=
    SET CONDA_PATH_BACKUP=
)

EXIT /B

:NORMALIZEPATH
    SET "%1=%~dpfn2"
    EXIT /B
