@echo off
setlocal

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
    echo "cannot find conda"
    exit /b 1

:runcondasecretcommand
REM activate conda root environment
FOR /F "delims=" %%i IN ('conda ..activateroot') DO set PATH=%%i

:resetprompt
set PROMPT=$P$G

endlocal & set PROMPT=%PROMPT%& set PATH=%PATH%& set CONDA_DEFAULT_ENV=
