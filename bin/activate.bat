@echo off

REM Should this be set globally on install?
if "%ANACONDA_ENVS%" == "" set ANACONDA_ENVS=C:\Anaconda\envs

if not "%1" == "" goto skipmissingarg
    echo Usage: condactivate envname
    echo.
    echo Deactivates previously activated Anaconda
    echo environment, then activates the chosen one.
    exit /b 1
:skipmissingarg

if exist "%ANACONDA_ENVS%\%1\Python.exe" goto skipmissingenv
    echo No environment named "%1" exists in %ANACONDA_ENVS%
    exit /b 1
:skipmissingenv

REM Deactivate a previous activation if it is live
if "%CONDACTIVATED%" == "" goto skipdeactivate
    REM This search/replace removes the previous env from the path
    echo Deactivating environment "%CONDACTIVATED%"...
    set CONDACTIVATE_PATH=%ANACONDA_ENVS%\%CONDACTIVATED%;%ANACONDA_ENVS%\%CONDACTIVATED%\Scripts;
    call set PATH=%%PATH:%CONDACTIVATE_PATH%=%%
    set CONDACTIVATED=
    set CONDACTIVATE_PATH=
:skipdeactivate

set CONDACTIVATED=%1
echo Activating environment "%CONDACTIVATED%"...
set PATH=%ANACONDA_ENVS%\%CONDACTIVATED%;%ANACONDA_ENVS%\%CONDACTIVATED%\Scripts;%PATH%
