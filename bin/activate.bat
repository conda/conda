@echo off

for /f "delims=" %%i in ("%~dp0..\envs") do (
    set ANACONDA_ENVS=%%~fi
)

set CONDA_NEW_ENV=%~1

if "%~2" == "" goto skiptoomanyargs
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

if exist "%ANACONDA_ENVS%\%CONDA_NEW_ENV%\conda-meta" goto skipmissingenv
    echo No environment named "%CONDA_NEW_ENV%" exists in %ANACONDA_ENVS%
    set CONDA_NEW_ENV=
    exit /b 1
:skipmissingenv

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
    set CONDACTIVATE_PATH=
:skipdeactivate

set CONDA_ENV_PATH=%ANACONDA_ENVS%\%CONDA_DEFAULT_ENV%
set CONDA_DEFAULT_ENV=%CONDA_NEW_ENV%
set CONDA_NEW_ENV=
echo Activating environment "%CONDA_DEFAULT_ENV%"...
set PATH=%ANACONDA_ENVS%\%CONDA_DEFAULT_ENV%;%ANACONDA_ENVS%\%CONDA_DEFAULT_ENV%\Scripts;%PATH%
set CONDA_OLD_PROMPT=%PROMPT%
set PROMPT=[%CONDA_DEFAULT_ENV%] %PROMPT%

REM Run any activate scripts
if not exist "%ANACONDA_ENVS%\%CONDA_DEFAULT_ENV%\etc\conda\activate.d" goto noactivate
    pushd "%ANACONDA_ENVS%\%CONDA_DEFAULT_ENV%\etc\conda\activate.d"
    for %%g in (*.bat) do call "%%g"
    popd
:noactivate
