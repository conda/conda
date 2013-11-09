@echo off

for /f %%i in ("%~dp0..\envs") do (
    set ANACONDA_ENVS=%%~fi
)

if not "%1" == "" goto skipmissingarg
    echo Usage: activate envname
    echo.
    echo Deactivates previously activated Conda
    echo environment, then activates the chosen one.
    exit /b 1
:skipmissingarg

if exist "%ANACONDA_ENVS%\%1\Python.exe" goto skipmissingenv
    echo No environment named "%1" exists in %ANACONDA_ENVS%
    exit /b 1
:skipmissingenv

REM Deactivate a previous activation if it is live
if "%CONDA_DEFAULT_ENV%" == "" goto skipdeactivate
    REM This search/replace removes the previous env from the path
    echo Deactivating environment "%CONDA_DEFAULT_ENV%"...
    set CONDACTIVATE_PATH=%ANACONDA_ENVS%\%CONDA_DEFAULT_ENV%;%ANACONDA_ENVS%\%CONDA_DEFAULT_ENV%\Scripts;
    call set PATH=%%PATH:%CONDACTIVATE_PATH%=%%
    set CONDA_DEFAULT_ENV=
    set CONDACTIVATE_PATH=
:skipdeactivate

set CONDA_DEFAULT_ENV=%1
echo Activating environment "%CONDA_DEFAULT_ENV%"...
set PATH=%ANACONDA_ENVS%\%CONDA_DEFAULT_ENV%;%ANACONDA_ENVS%\%CONDA_DEFAULT_ENV%\Scripts;%PATH%
set PROMPT=[%1] $P$G
