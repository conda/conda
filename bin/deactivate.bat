@echo off
SETLOCAL ENABLEDELAYEDEXPANSION

if "%1" == "" goto skipmissingarg
    echo Usage: deactivate
    echo.
    echo Deactivates previously activated Conda
    echo environment.
    exit /b 1
:skipmissingarg

REM special case for root env:
REM   Checks for Library\bin on PATH.  If exists, we have root env on PATH.
call :NORMALIZEPATH ROOT_PATH "%~dp0.."
CALL SET "PATH_NO_ROOT=%%PATH:%ROOT_PATH%;=%%"
IF NOT "%PATH_NO_ROOT%"=="%PATH%" SET "CONDA_DEFAULT_ENV=%ROOT_PATH%"

REM Deactivate a previous activation if it is live
if "%CONDA_DEFAULT_ENV%" == "" goto skipdeactivate
    REM This search/replace removes the previous env from the path
    echo Deactivating environment "%CONDA_DEFAULT_ENV%"...

    REM Run any deactivate scripts
    if not exist "%CONDA_DEFAULT_ENV%\etc\conda\deactivate.d" goto nodeactivate
        pushd "%CONDA_DEFAULT_ENV%\etc\conda\deactivate.d"
        for %%g in (*.bat) do call "%%g"
        popd
    :nodeactivate

    REM Remove env name from PROMPT
    FOR /F "tokens=* delims=\" %%i IN ("%CONDA_DEFAULT_ENV%") DO SET "CONDA_OLD_ENV_NAME=%%~ni"
    call set PROMPT=%%PROMPT:[%CONDA_OLD_ENV_NAME%] =%%

    SET "CONDACTIVATE_PATH=%CONDA_DEFAULT_ENV%;%CONDA_DEFAULT_ENV%\Scripts;%CONDA_DEFAULT_ENV%\Library\bin;"
    CALL SET "PATH=%%PATH:%CONDACTIVATE_PATH%=%%"
:skipdeactivate

REM Make sure that root's Scripts dir is on PATH, for sake of keeping activate/deactivate available.
CALL SET "PATH_NO_SCRIPTS=%%PATH:%~dp0;=%%"
IF "%PATH_NO_SCRIPTS%"=="%PATH%" SET "PATH=%PATH%;%~dp0;"

ENDLOCAL & (
    SET "PATH=%PATH%"
    SET "PROMPT=%PROMPT%"
    SET CONDA_DEFAULT_ENV=
)

EXIT /B

:NORMALIZEPATH
    SET "%1=%~dpfn2"
    EXIT /B
