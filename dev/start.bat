@CALL :CLEANUP

:: preserve script for help
@SET "_SCRIPT=%~0"

:: get source path
@PUSHD "%~dp0\.."
@SET "_SRC=%CD%"
@POPD

:: parse args
:ARGS_LOOP
@IF "%~1"=="" @GOTO :ARGS_END

:: convert to uppercase
@FOR /F "usebackq delims=" %%I IN (`powershell.exe "'%~1'.toUpper()"`) DO @SET "_ARG=%%~I"

@IF "%_ARG%"=="/P" (
    @SET "_PYTHON=%~2"
    @SHIFT
    @SHIFT
    @GOTO :ARGS_LOOP
)
@IF "%_ARG%"=="/U" (
    @SET "_UPDATE=0"
    @SHIFT
    @GOTO :ARGS_LOOP
)
@IF "%_ARG%"=="/D" (
    @SET "_DEVENV=%~2"
    @SHIFT
    @SHIFT
    @GOTO :ARGS_LOOP
)
@IF "%_ARG%"=="/N" (
    @SET "_DRYRUN=0"
    @SHIFT
    @GOTO :ARGS_LOOP
)
@IF "%_ARG%"=="/?" (
    @ECHO Usage: %_SCRIPT% [options]
    @ECHO.
    @ECHO Options:
    @ECHO   /P  VERSION  Python version for the env to activate. ^(default: 3.10^)
    @ECHO   /U           Force update packages. ^(default: update every 24 hours^)
    @ECHO   /D  PATH     Path to base env install, can also be defined in ~\.condarc.
    @ECHO                Path is appended with Windows. ^(default: devenv^)
    @ECHO   /N           Display env to activate. ^(default: false^)
    @ECHO.  /?           Display this.
    @EXIT /B 0
)
@ECHO Error: unknown option %~1 1>&2
@EXIT /B 1
:ARGS_END

:: fallback to default values
@IF "%_PYTHON%"=="" @SET "_PYTHON=3.10"
@IF "%_UPDATE%"=="" @SET "_UPDATE=1"
@IF "%_DRYRUN%"=="" @SET "_DRYRUN=1"

:: read devenv from ~\.condarc
@IF "%_DEVENV%"=="" @CALL :CONDARC
:: fallback to devenv in source default
@IF "%_DEVENV%"=="" @SET "_DEVENV=%_SRC%\devenv"
:: installer location
@SET "_INSTALLER=%_DEVENV%"
:: include OS
@SET "_DEVENV=%_DEVENV%\Windows"
:: ensure exists
@IF %_DRYRUN%==1 @IF NOT EXIST "%_DEVENV%" @MKDIR "%_DEVENV%"

:: other environment variables
@SET "_NAME=devenv-%_PYTHON%-c"
@SET "_ENV=%_DEVENV%\envs\%_NAME%"
@SET "_UPDATED=%_ENV%\.devenv-updated"
@SET "_BASEEXE=%_DEVENV%\Scripts\conda.exe"
@SET "_ENVEXE=%_ENV%\Scripts\conda.exe"
@SET "_PYTHONEXE=%_ENV%\python.exe"
@SET "_CONDABAT=%_ENV%\condabin\conda.bat"
@SET "_CONDAHOOK=%_ENV%\condabin\conda_hook.bat"

:: dry-run printout
@IF %_DRYRUN%==0 @GOTO :DRYRUN

:: deactivate any prior envs
@IF "%CONDA_SHLVL%"=="" @GOTO DEACTIVATED
@IF %CONDA_SHLVL%==0 @GOTO DEACTIVATED
@ECHO Deactivating %CONDA_SHLVL% environment(s)...
:DEACTIVATING
@IF "%CONDA_SHLVL%"=="0" @GOTO DEACTIVATED
@CALL conda deactivate
@IF NOT %ErrorLevel%==0 (
    @ECHO Error: failed to deactivate environment^(s^) 1>&2
    @EXIT /B 1
)
@GOTO DEACTIVATING
:DEACTIVATED

:: does miniconda install exist?
@IF EXIST "%_DEVENV%\conda-meta\history" @GOTO INSTALLED

:: downloading miniconda
@IF EXIST "%_INSTALLER%\miniconda.exe" @GOTO DOWNLOADED
@ECHO Downloading miniconda...
@powershell.exe "$ProgressPreference = 'SilentlyContinue'; Invoke-WebRequest -Uri 'https://repo.anaconda.com/miniconda/Miniconda3-latest-Windows-x86_64.exe' -OutFile '%_INSTALLER%\miniconda.exe' | Out-Null"
@IF NOT %ErrorLevel%==0 (
    @ECHO Error: failed to download miniconda 1>&2
    @EXIT /B 1
)
:DOWNLOADED

:: installing miniconda
@ECHO Installing development environment...
@START /wait "" "%_INSTALLER%\miniconda.exe" /InstallationType=JustMe /RegisterPython=0 /AddToPath=0 /S /D=%_DEVENV% > NUL
@IF NOT %ErrorLevel%==0 (
    @ECHO Error: failed to install development environment 1>&2
    @EXIT /B 1
)
:: Windows doesn't ship with git so ensure installed into base otherwise auxlib will act up
@CALL :CONDA "%_BASEEXE%" install -yq --name base defaults::git > NUL
:INSTALLED

:: create empty env if it doesn't exist
@IF EXIST "%_ENV%" @GOTO ENVEXISTS
@ECHO Creating %_NAME%...

@CALL :CONDA "%_BASEEXE%" create -yq --prefix "%_ENV%" > NUL
@IF NOT %ErrorLevel%==0 (
    @ECHO Error: failed to create %_NAME% 1>&2
    @EXIT /B 1
)
:ENVEXISTS

:: check if explicitly updating or if 24 hrs since last update
@CALL :UPDATING
@IF NOT %ErrorLevel%==0 @GOTO UPTODATE
@ECHO Updating %_NAME%...

@CALL :CONDA "%_BASEEXE%" update -yq --all > NUL
@IF NOT %ErrorLevel%==0 (
    @ECHO Error: failed to update development environment 1>&2
    @EXIT /B 1
)

@CALL :CONDA "%_BASEEXE%" install ^
    -yq ^
    --prefix "%_ENV%" ^
    --override-channels ^
    -c defaults ^
    --file "%_SRC%\tests\requirements.txt" ^
    --file "%_SRC%\tests\requirements-ci.txt" ^
    --file "%_SRC%\tests\requirements-Windows.txt" ^
    "python=%_PYTHON%" > NUL
@IF NOT %ErrorLevel%==0 (
    @ECHO Error: failed to update %_NAME% 1>&2
    @EXIT /B 1
)

:: update timestamp
@IF EXIST "%_UPDATED%" @DEL "%_UPDATED%"
@ECHO > "%_UPDATED%"
:UPTODATE

:: initialize conda command
@ECHO Initializing shell integration...
@CALL "%_CONDAHOOK%"
@IF NOT %ErrorLevel%==0 (
    @ECHO Error: failed to initialize shell integration 1>&2
    @EXIT /B 1
)

:: activate env
@ECHO Activating %_NAME%...
@CALL conda activate "%_ENV%" > NUL
@IF NOT %ErrorLevel%==0 (
    @ECHO Error: failed to activate %_NAME% 1>&2
    @EXIT /B 1
)
@SET "CONDA_BAT=%_CONDABAT%"
@DOSKEY conda="%CONDA_BAT%" $*

:: "install" conda
@SET "PYTHONPATH=%_SRC%;%PYTHONPATH%"

:CLEANUP
@SET _ARG=
@SET _BASEEXE=
@SET _CONDABAT=
@SET _DEVENV=
@SET _DRYRUN=
@SET _ENV=
@SET _ENVEXE=
@SET _INSTALLER=
@SET _NAME=
@SET _PATH=
@SET _PYTHON=
@SET _PYTHONEXE=
@SET _SCRIPT=
@SET _SRC=
@SET _UPDATE=
@SET _UPDATED=
@GOTO :EOF

:CONDA *args
:: include OpenSSL & git on %PATH%
@SET "_PATH=%PATH%"
@SET "PATH=%_DEVENV%\Library\bin;%PATH%"

@CALL %*
@IF NOT %ErrorLevel%==0 @EXIT /B %ErrorLevel%

:: restore %PATH%
@SET "PATH=%_PATH%"
@SET _PATH=
@GOTO :EOF

:CONDARC
:: read devenv from ~\.condarc
:: check if ~\.condarc exists
@IF NOT EXIST "%USERPROFILE%\.condarc" @EXIT /B 2
:: check if devenv key is defined
@FINDSTR /R /C:"^devenv:" "%USERPROFILE%\.condarc" > NUL
@IF NOT %ErrorLevel%==0 @EXIT /B 1
:: read devenv key
@FOR /F "usebackq delims=" %%I IN (`powershell.exe "(Select-String -Path '~\.condarc' -Pattern '^devenv:\s*(.+)' | Select-Object -Last 1).Matches.Groups[1].Value -replace '^~',""$Env:UserProfile"""`) DO @SET "_DEVENV=%%~fI"
@GOTO :EOF

:UPDATING
:: check if explicitly updating or if 24 hrs since last update
@IF %_UPDATE%==0 @EXIT /B 0
@IF NOT EXIST "%_UPDATED%" @EXIT /B 0
@powershell.exe "Exit (Get-Item '"%_UPDATED%"').LastWriteTime -ge (Get-Date).AddHours(-24)"
@EXIT /B %ErrorLevel%

:DRYRUN
:: dry-run printout
@ECHO Python: %_PYTHON%
@CALL :UPDATING
@IF %ErrorLevel%==0 (
    @ECHO Updating: [yes]
) ELSE (
    @ECHO Updating: [no]
)
@IF EXIST "%_DEVENV%" (
    @ECHO Devenv: %_DEVENV% [exists]
) ELSE (
    @ECHO Devenv: %_DEVENV% [pending]
)
@ECHO.
@ECHO Name: %_NAME%
@IF EXIST "%_ENV%" (
    @ECHO Path: %_ENV% [exists]
) ELSE (
    @ECHO Path: %_ENV% [pending]
)
@ECHO.
@ECHO Source: %_SRC%
@EXIT /B 0
