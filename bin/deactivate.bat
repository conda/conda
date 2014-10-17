@echo off

for /f "delims=" %%i in ("%~dp0..\envs") do (
    set ANACONDA_ENVS=%%~fi
)

if not "%1" == "--help" goto skipusage
    (
    echo Usage: deactivate
    echo.
    echo Deactivates previously activated Conda
    echo environment.
    ) 1>&2
    exit /b 1
:skipusage

if "%1" == "" goto skiptoomanyargs
    (echo Error: too many arguments.) 1>&2
    exit /b 1
:skiptoomanyargs

REM Use conda itself to figure things out
REM No conda, no dice

SET CONDAFOUND=
for %%X in (conda.exe) do (set CONDAFOUND=%%~$PATH:X)
if not defined CONDAFOUND for %%X in (conda.bat) do (set CONDAFOUND=%%~$PATH:X)
if defined CONDAFOUND goto runcondasecretcommand
    echo "cannot find conda to test for the environment %CONDA_NEW_ENV%"
    exit /b 1

:runcondasecretcommand
set NEWPATH=
FOR /F "delims=" %%i IN ('conda ..activateroot') DO set PATH=%%i
set CONDA_DEFAULT_ENV=
set CONDACTIVATE_PATH=

:resetprompt
set PROMPT=$P$G
