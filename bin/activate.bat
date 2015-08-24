@echo off
REM Check for CONDA_EVS_PATH environment variable
REM It it doesn't exist, look inside the Anaconda install tree
if "%CONDA_ENVS_PATH%" == "" (
set CONDA_ENVS_PATH="%~dp0..\envs"
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

REM Search through paths in CONDA_ENVS_PATH 
REM First match will be the one used
set FOUND_ENV=0
for %%F in ("%CONDA_ENVS_PATH:;=" "%") do (
  if exist "%%~F\%CONDA_NEW_ENV%\conda-meta" (
    set ANACONDA_ENVS=%%~F
    set FOUND_ENV=1
   )
)

if %FOUND_ENV%==1 goto skipmissingenv
    echo No environment named "%CONDA_NEW_ENV%" exists in %CONDA_ENVS_PATH%
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

    set "CONDACTIVATE_PATH=%ANACONDA_ENVS%\%CONDA_DEFAULT_ENV%;%ANACONDA_ENVS%\%CONDA_DEFAULT_ENV%\Scripts;%ANACONDA_ENVS%\%CONDA_DEFAULT_ENV%\Library\bin"
    call set PATH=%%PATH:%CONDACTIVATE_PATH%=%%
    set CONDA_DEFAULT_ENV=
    set CONDACTIVATE_PATH=
    set PROMPT=%CONDA_OLD_PROMPT%
    set CONDA_OLD_PROMPT=
:skipdeactivate

set CONDA_DEFAULT_ENV=%CONDA_NEW_ENV%
set CONDA_NEW_ENV=
set "CONDA_ENV_PATH=%ANACONDA_ENVS%\%CONDA_DEFAULT_ENV%"
echo Activating environment "%CONDA_DEFAULT_ENV%"...
set "PATH=%ANACONDA_ENVS%\%CONDA_DEFAULT_ENV%;%ANACONDA_ENVS%\%CONDA_DEFAULT_ENV%\Scripts;%ANACONDA_ENVS%\%CONDA_DEFAULT_ENV%\Library\bin;%PATH%"

if not "%CONDA_OLD_PROMPT%" == "" goto skipoldprompt
    set CONDA_OLD_PROMPT=%PROMPT%
:skipoldprompt
set PROMPT=[%CONDA_DEFAULT_ENV%] %CONDA_OLD_PROMPT%

REM Run any activate scripts
if not exist "%ANACONDA_ENVS%\%CONDA_DEFAULT_ENV%\etc\conda\activate.d" goto noactivate
    pushd "%ANACONDA_ENVS%\%CONDA_DEFAULT_ENV%\etc\conda\activate.d"
    for %%g in (*.bat) do call "%%g"
    popd
:noactivate
