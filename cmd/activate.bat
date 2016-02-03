@echo off
setlocal enabledelayedexpansion

set "CONDA_NEW_ENV=%~1"

if "%2" == "" goto skiptoomanyargs
    (echo Error: did not expect more than one argument.) 1>&2
    exit /b 1
:skiptoomanyargs

if not "%1" == "" goto skipmissingarg
    :: Set env to root if no arg provided
    set CONDA_NEW_ENV=root
:skipmissingarg

SET "CONDA_EXE=%~dp0\..\Scripts\conda.exe"

REM Ensure that path or name passed is valid before deactivating anything
call "%CONDA_EXE%" ..checkenv "%CONDA_NEW_ENV%"
if errorlevel 1 exit /b 1

call %~dp0\deactivate.bat

REM take a snapshot of pristine state for later
SET "CONDA_PATH_BACKUP=%PATH%"
REM Activate the new environment
FOR /F "delims=" %%i IN ('call "%CONDA_EXE%" ..activate "%CONDA_NEW_ENV%"') DO set "PATH=%%i"
if errorlevel 1 exit /b 1

REM take a snapshot of pristine state for later
set "CONDA_OLD_PS1=%PROMPT%"
FOR /F "delims=" %%i IN ('call "%CONDA_EXE%" ..setps1 "%CONDA_NEW_ENV%" "%PROMPT%"') DO set "PROMPT=%%i"
if errorlevel 1 exit /b 1

REM Replace CONDA_NEW_ENV with the full path, if it is anything else
REM   (name or relative path).  This is to remove any ambiguity.
for /F "tokens=1 delims=;" %%i in ("%PATH%") do set "CONDA_NEW_ENV=%%i"

REM This persists env variables, which are otherwise local to this script right now.
endlocal & (
    REM Used for deactivate, to make sure we restore original state after deactivation
    SET "CONDA_PATH_BACKUP=%CONDA_PATH_BACKUP%"
    SET "CONDA_OLD_PS1=%CONDA_OLD_PS1%"
    set "PROMPT=%PROMPT%"
    set "PATH=%PATH%"
    set "CONDA_DEFAULT_ENV=%CONDA_NEW_ENV%"
    )
