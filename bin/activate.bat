@echo off

for /f "delims=" %%i in ("%~dp0..\envs") do (
    set ANACONDA_ENVS=%%~fi
)

set CONDA_NEW_NAME=%~1

if "%~2" == "" goto skiptoomanyargs
    echo ERROR: Too many arguments provided
    goto usage
:skiptoomanyargs

if not "%CONDA_NEW_NAME%" == "" goto skipmissingarg
:usage
    echo Usage: activate envname
    echo.
    echo Deactivates previously activated Conda
    echo environment, then activates the chosen one.
    exit /b 1
:skipmissingarg

if exist "%ANACONDA_ENVS%\%CONDA_NEW_NAME%\conda-meta" goto usenamedenv
    for /F %%i in ("%CONDA_NEW_NAME%") do set CONDA_NEW_PATH=%%~fi
    if exist "%CONDA_NEW_PATH%\conda-meta" goto usefullpath
        echo No environment named "%CONDA_NEW_NAME%" exists in %ANACONDA_ENVS%
        set CONDA_NEW_NAME=
        set CONDA_NEW_PATH=
        exit /b 1
:usenamedenv
    set CONDA_NEW_PATH=%ANACONDA_ENVS%\%CONDA_NEW_NAME%
    goto skipmissingenv
:usefullpath
    for /F %%i in ("%CONDA_NEW_PATH%") do set CONDA_NEW_NAME=%%~ni
:skipmissingenv

REM Deactivate a previous activation if it is live
if "%CONDA_DEFAULT_ENV%" == "" goto skipdeactivate
    REM This search/replace removes the previous env from the path
    echo Deactivating environment "%CONDA_DEFAULT_ENV%"...

    REM Run any deactivate scripts
    if not exist "%CONDA_DEFAULT_ENV%\etc\conda\deactivate.d" goto nodeactivate
        pushd "%CONDA_DEFAULT_ENV%\etc\conda\deactivate.d"
        for %%g in (*.bat) do call "%%g"
        popd
    :nodeactivate

    set CONDACTIVATE_PATH="%CONDA_DEFAULT_ENV%";"%CONDA_DEFAULT_ENV%\Scripts";"%CONDA_DEFAULT_ENV%\Library\bin"
    call set PATH=%%PATH:%CONDACTIVATE_PATH%=%%
    set CONDA_DEFAULT_ENV=
    set CONDACTIVATE_PATH=
    set PROMPT=%CONDA_OLD_PROMPT%
    set CONDA_OLD_PROMPT=
:skipdeactivate

set CONDA_DEFAULT_ENV=%CONDA_NEW_PATH%
echo Activating environment "%CONDA_DEFAULT_ENV%"...
set PATH="%CONDA_DEFAULT_ENV%";"%CONDA_DEFAULT_ENV%\Scripts";"%CONDA_DEFAULT_ENV%\Library\bin";%PATH%
set PROMPT=[%CONDA_NEW_NAME%] $P$G
set CONDA_NEW_NAME=
set CONDA_NEW_PATH=

REM Run any activate scripts
if not exist "%CONDA_DEFAULT_ENV%\etc\conda\activate.d" goto noactivate
    pushd "%CONDA_DEFAULT_ENV%\etc\conda\activate.d"
    for %%g in (*.bat) do call "%%g"
    popd
:noactivate
