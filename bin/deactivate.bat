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


REM Deactivate a previous activation if it is live
if "%CONDA_DEFAULT_ENV%" == "" goto skipdeactivate
    REM This search/replace removes the previous env from the path
    echo Deactivating environment "%CONDA_DEFAULT_ENV%"...

    REM Run any deactivate scripts
    if not exist "%ANACONDA_ENVS%\%CONDA_DEFAULT_ENV%\etc\conda\deactivate.d" goto nodeactivate
        pushd "%ANACONDA_ENVS%\%CONDA_DEFAULT_ENV%\etc\conda\deactivate.d"
        for %%g in (*.bat) do call "%%g"
        popd
    :nodeactivate

    set CONDACTIVATE_PATH=%ANACONDA_ENVS%\%CONDA_DEFAULT_ENV%;%ANACONDA_ENVS%\%CONDA_DEFAULT_ENV%\Scripts;
    call set PATH=%%PATH:%CONDACTIVATE_PATH%=%%
    set CONDA_DEFAULT_ENV=
    set CONDA_ENV_PATH=
    set CONDACTIVATE_PATH=
:skipdeactivate

set PROMPT=%CONDA_OLD_PROMPT%
set CONDA_OLD_PROMPT=
