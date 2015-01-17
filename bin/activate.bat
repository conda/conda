@echo off
setlocal

set CONDA_NEW_ENV=%1
set CONDA_NEW_ENV=%CONDA_NEW_ENV:"=%

if "%2" == "" goto skiptoomanyargs
    (echo Error: did not expect more than one argument.) 1>&2
    exit /b 1
:skiptoomanyargs

if not "%1" == "" goto skipmissingarg
    (echo Error: no environment provided.) 1>&2
    exit /b 1
:skipmissingarg

if not "%1" == "--help" goto skipusage
    (
    echo Usage: activate ENV
    echo.
    echo Deactivates previously activated Conda
    echo environment, then activates the chosen one.
    ) 1>&2
    exit /b 1
:skipusage

REM Use conda itself to figure things out
REM No conda, no dice

SET CONDAFOUND=
for %%X in (conda.exe) do (set CONDAFOUND=%%~$PATH:X)
if not defined CONDAFOUND for %%X in (conda.bat) do (set CONDAFOUND=%%~$PATH:X)
if defined CONDAFOUND goto runcondasecretcommand
    echo "cannot find conda to test for the environment %CONDA_NEW_ENV%"
    exit /b 1

:runcondasecretcommand
REM Run secret conda ..checkenv command
call "%CONDAFOUND%" ..checkenv %CONDA_NEW_ENV%
REM EQU 0 means 0 or above on Windows ;(
if %ERRORLEVEL% EQU 1 (
    exit /b 1
)

REM Deactivate a previous activation if it is live
FOR /F "delims=" %%i IN ('"%CONDAFOUND%" ..deactivate') DO set PATH=%%i

REM Activate the new environment
FOR /F "delims=" %%i IN ('"%CONDAFOUND%" ..activate %CONDA_NEW_ENV%') DO set PATH=%%i

for /F %%C IN ('"%CONDAFOUND%" ..changeps1') DO set CHANGEPS1=%%C
if "%CHANGEPS1%" == "1" set PROMPT=[%CONDA_NEW_ENV%] $P$G

endlocal & set PROMPT=%PROMPT%& set PATH=%PATH%& set CONDA_DEFAULT_ENV=%CONDA_NEW_ENV%
