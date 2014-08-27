@echo off

for /f "delims=" %%i in ("%~dp0..\envs") do (
    set ANACONDA_ENVS=%%~fi
)

if "%1" == "" goto skipmissingarg
    echo Usage: deactivate
    echo.
    echo Deactivates previously activated Conda
    echo environment.
    exit /b 1
:skipmissingarg

REM Use conda itself to figure things out
REM No conda, no dice

SET CONDAFOUND=
for %%X in (conda.exe) do (set CONDAFOUND=%%~$PATH:X)
if defined CONDAFOUND goto runcondasecretcommand
    echo "cannot find conda to test for the environment %CONDA_NEW_ENV%"
    exit /b 1

:runcondasecretcommand
REM Deactivate a previous activation if it is live
if "%CONDA_DEFAULT_ENV%" == "" goto skipdeactivate
    REM This search/replace removes the previous env from the path
    echo Deactivating environment "%CONDA_DEFAULT_ENV%"...
    set NEWPATH=
    FOR /F "delims=" %%i IN ('conda ..deactivate') DO set NEWPATH=%%i
    set PATH=%NEWPATH%
    set CONDA_DEFAULT_ENV=
    set CONDACTIVATE_PATH=

set PROMPT=$P$G
