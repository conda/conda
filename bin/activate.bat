@echo off
REM Check for CONDA_ENVS_PATH environment variable
REM It it doesn't exist, look inside the Anaconda install tree
if "%CONDA_ENVS_PATH%" == "" (
    REM turn relative path into absolute path
    FOR /F %%i IN ("%~dp0..\envs") DO set CONDA_ENVS_PATH=%%~fi
)

set CONDA_NEW_NAME=%~1

if "%~2" == "" goto skiptoomanyargs
    echo ERROR: Too many arguments provided
    goto usage
:skiptoomanyargs

if "%CONDA_NEW_NAME%" == "" set CONDA_NEW_NAME=%~dp0..\

REM Search through paths in CONDA_ENVS_PATH
REM First match will be the one used

for %%F in ("%CONDA_ENVS_PATH:;=" "%") do (
    if exist "%%~F\%CONDA_NEW_NAME%\conda-meta" (
       set CONDA_NEW_PATH=%%~F\%CONDA_NEW_NAME%
       goto found_env
    )
)

if exist "%CONDA_NEW_NAME%\conda-meta" (
    set CONDA_NEW_PATH=%CONDA_NEW_NAME%
    ) else (
    echo No environment named "%CONDA_NEW_NAME%" exists in %CONDA_ENVS_PATH%, or is not a valid conda installation directory.
    set CONDA_NEW_NAME=
    set CONDA_NEW_PATH=
    exit /b 1
)

:found_env

for /F %%i in ("%CONDA_NEW_PATH%") do set CONDA_NEW_NAME=%%~ni

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

    set CONDACTIVATE_PATH=%CONDA_DEFAULT_ENV%;%CONDA_DEFAULT_ENV%\Scripts;%CONDA_DEFAULT_ENV%\Library\bin;
    call set PATH=%%PATH:%CONDACTIVATE_PATH%=%%
    set CONDA_DEFAULT_ENV=
    set CONDACTIVATE_PATH=
    set PROMPT=%CONDA_OLD_PROMPT%
    set CONDA_OLD_PROMPT=
:skipdeactivate

set CONDA_DEFAULT_ENV=%CONDA_NEW_PATH%
echo Activating environment "%CONDA_DEFAULT_ENV%"...
set PATH=%CONDA_DEFAULT_ENV%;%CONDA_DEFAULT_ENV%\Scripts;%CONDA_DEFAULT_ENV%\Library\bin;%PATH%
IF "%CONDA_NEW_NAME%"=="" (
   set PROMPT=$P$G
   REM Clear CONDA_DEFAULT_ENV so that this is truly a "root" environment, not an environment pointed at root
   set CONDA_DEFAULT_ENV=
   ) ELSE (
   set PROMPT=[%CONDA_NEW_NAME%] $P$G
)
set CONDA_NEW_NAME=
set CONDA_NEW_PATH=

REM Run any activate scripts
if not exist "%CONDA_DEFAULT_ENV%\etc\conda\activate.d" goto noactivate
    pushd "%CONDA_DEFAULT_ENV%\etc\conda\activate.d"
    for %%g in (*.bat) do call "%%g"
    popd
:noactivate
