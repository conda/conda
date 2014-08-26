@echo off

for /f "delims=" %%i in ("%~dp0..\envs") do (
    set ANACONDA_ENVS=%%~fi
)

set CONDA_NEW_ENV=%1
set CONDA_NEW_ENV=%CONDA_NEW_ENV:"=%

if "%2" == "" goto skiptoomanyargs
    echo ERROR: Too many arguments provided
    goto usage
:skiptoomanyargs

if not "%CONDA_NEW_ENV%" == "" goto skipmissingarg
:usage
    echo Usage: activate envname
    echo.
    echo Deactivates previously activated Conda
    echo environment, then activates the chosen one.
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
REM Run secret conda ..checkenv command
conda ..checkenv %CONDA_NEW_ENV%
REM EQU 0 means 0 or above on Windows ;(
if %ERRORLEVEL% EQU 1 (
    exit /b 1
)

REM Deactivate a previous activation if it is live
if "%CONDA_DEFAULT_ENV%" == "" goto skipdeactivate
    REM This search/replace removes the previous env from the path
    echo Deactivating environment "%CONDA_DEFAULT_ENV%"...
    set CONDACTIVATE_PATH=%ANACONDA_ENVS%\%CONDA_DEFAULT_ENV%;%ANACONDA_ENVS%\%CONDA_DEFAULT_ENV%\Scripts;
    call set PATH=%%PATH:%CONDACTIVATE_PATH%=%%
    set CONDA_DEFAULT_ENV=
    set CONDACTIVATE_PATH=
:skipdeactivate

set CONDA_DEFAULT_ENV=%CONDA_NEW_ENV%
REM set CONDA_NEW_ENV=
echo Activating environment "%CONDA_DEFAULT_ENV%"...
set NEWPATH=
FOR /F "delims=" %%i IN ('conda ..activate %CONDA_NEW_ENV%') DO set NEWPATH=%%i
set PATH=%NEWPATH%;%NEWPATH%\Scripts;%PATH%
set PROMPT=[%CONDA_DEFAULT_ENV%] $P$G
