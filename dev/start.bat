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
@FOR /F "usebackq delims=" %%I IN (`powershell.exe -NoProfile -Command "'%~1'.toUpper()"`) DO @SET "_ARG=%%~I"

@IF "%_ARG%"=="/P" (
    @SET "_PYTHON=%~2"
    @SHIFT
    @SHIFT
    @GOTO :ARGS_LOOP
)
@IF "%_ARG%"=="/I" (
    @SET "_INSTALLER_TYPE=%~2"
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
    @ECHO   /P  VERSION    Python version for the env to activate. ^(default: 3.10^)
    @ECHO   /I  INSTALLER  Installer to use: miniconda or miniforge, can also be defined in ~\.condarc. ^(default: miniconda^)
    @ECHO   /U             Force update packages. ^(default: update every 24 hours^)
    @ECHO   /D  PATH       Path to base env install, can also be defined in ~\.condarc.
    @ECHO                  Path is appended with Windows. ^(default: devenv^)
    @ECHO   /N             Display env to activate. ^(default: false^)
    @ECHO   /?             Display this.
    @EXIT /B 0
)
@ECHO Error: unknown option %~1 1>&2
@EXIT /B 1
:ARGS_END

:: read values from ~\.condarc if not set
@IF "%_DEVENV%"=="" @CALL :DEVENV_CONDARC
@IF "%_INSTALLER_TYPE%"=="" @CALL :INSTALLER_TYPE_CONDARC

:: prompt for installer type if not set
@IF NOT "%_INSTALLER_TYPE%"=="" @GOTO :SKIP_PROMPT
@ECHO Choose conda installer:
@ECHO   1^) miniconda ^(default - Anaconda defaults channel^)
@ECHO   2^) miniforge ^(conda-forge channel^)
@ECHO.
@ECHO Note: This choice can be overridden by setting the 'installer_type' key in ~\.condarc.
@ECHO.
@SET /P "_INSTALLER_TYPE=Enter choice [1]: "
:: terminated or empty prompt returns errorlevel 1, set default
@IF %ErrorLevel%==1 (
    @SET "_INSTALLER_TYPE=miniconda"
    @CALL :RESET_ERRORLEVEL
)
:: normalize user input
@IF "%_INSTALLER_TYPE%"=="1" @SET "_INSTALLER_TYPE=miniconda"
@IF "%_INSTALLER_TYPE%"=="2" @SET "_INSTALLER_TYPE=miniforge"
@IF NOT "%_INSTALLER_TYPE%"=="miniconda" @IF NOT "%_INSTALLER_TYPE%"=="miniforge" (
    @ECHO Error: invalid choice '%_INSTALLER_TYPE%'. Please run again and choose 1 or 2. 1>&2
    @EXIT /B 1
)
:SKIP_PROMPT

:: fallback to default values if not set
@IF "%_PYTHON%"=="" @SET "_PYTHON=3.10"
@IF "%_INSTALLER_TYPE%"=="" @SET "_INSTALLER_TYPE=miniconda"
@IF "%_DEVENV%"=="" @SET "_DEVENV=%_SRC%\devenv"
@IF "%_UPDATE%"=="" @SET "_UPDATE=1"
@IF "%_DRYRUN%"=="" @SET "_DRYRUN=1"

:: validate installer type
@IF "%_INSTALLER_TYPE%"=="miniconda" @GOTO :INSTALLER_VALID
@IF "%_INSTALLER_TYPE%"=="miniforge" @GOTO :INSTALLER_VALID
@ECHO Error: invalid installer type '%_INSTALLER_TYPE%'. Must be 'miniconda' or 'miniforge'. 1>&2
@EXIT /B 1
:INSTALLER_VALID

:: installer location is root devenv directory
@SET "_INSTALLER=%_DEVENV%\installers\Windows"

:: devenv include OS
@SET "_DEVENV=%_DEVENV%\Windows"

:: other environment variables
@SET "_NAME=devenv-%_PYTHON%-%_INSTALLER_TYPE%"
@SET "_ENV=%_DEVENV%\envs\%_NAME%"
@SET "_UPDATED=%_ENV%\.devenv-updated"
@SET "_BASEEXE=%_DEVENV%\Scripts\conda.exe"
@SET "_ENVEXE=%_ENV%\Scripts\conda.exe"
@SET "_PYTHONEXE=%_ENV%\python.exe"
@SET "_CONDABAT=%_ENV%\condabin\conda.bat"
@SET "_CONDAHOOK=%_ENV%\condabin\conda_hook.bat"

:: set installer-specific values
@IF "%_INSTALLER_TYPE%"=="miniconda" (
    @SET "_INSTALLER_FILE=%_INSTALLER%\miniconda.exe"
    @SET "_DOWNLOAD_URL=https://repo.anaconda.com/miniconda/Miniconda3-latest-Windows-x86_64.exe"
) ELSE IF "%_INSTALLER_TYPE%"=="miniforge" (
    @SET "_INSTALLER_FILE=%_INSTALLER%\miniforge.exe"
    @SET "_DOWNLOAD_URL=https://github.com/conda-forge/miniforge/releases/latest/download/Miniforge3-Windows-x86_64.exe"
)

:: dryrun printout
@IF %_DRYRUN%==0 @GOTO :DRYRUN

:: ensure installer and devenv directories exist
@IF NOT EXIST "%_INSTALLER%" @MKDIR "%_INSTALLER%"
@IF NOT EXIST "%_DEVENV%" @MKDIR "%_DEVENV%"

:: deactivate any prior envs
@IF "%CONDA_SHLVL%"=="" @GOTO :DEACTIVATED
@IF %CONDA_SHLVL%==0 @GOTO :DEACTIVATED
@ECHO Deactivating %CONDA_SHLVL% environment(s)...
:DEACTIVATING
@IF "%CONDA_SHLVL%"=="0" @GOTO :DEACTIVATED
@CALL conda deactivate
@IF NOT %ErrorLevel%==0 (
    @ECHO Error: failed to deactivate environment^(s^) 1>&2
    @EXIT /B 1
)
@GOTO :DEACTIVATING
:DEACTIVATED

:: does conda install exist?
@IF EXIST "%_DEVENV%\conda-meta\history" @GOTO :INSTALLED

:: Remove zero-byte installer files before download
@IF EXIST "%_INSTALLER_FILE%" (
    @IF NOT EXIST "%_INSTALLER_FILE%" (
        REM File does not exist, skip
    ) ELSE (
        @FOR %%F IN ("%_INSTALLER_FILE%") DO @IF %%~zF EQU 0 (
            @ECHO Warning: removing empty installer file %_INSTALLER_FILE%
            @DEL /F /Q "%_INSTALLER_FILE%"
        )
    )
)

@IF EXIST "%_INSTALLER_FILE%" @GOTO :DOWNLOADED
@ECHO Downloading %_INSTALLER_TYPE%...
@powershell.exe -NoProfile -Command "$ProgressPreference = 'SilentlyContinue'; Invoke-WebRequest -Uri '%_DOWNLOAD_URL%' -OutFile '%_INSTALLER_FILE%' | Out-Null"
@FOR %%F IN ("%_INSTALLER_FILE%") DO @IF NOT EXIST "%%F" (
    @ECHO Error: failed to download %_INSTALLER_TYPE% (file missing) 1>&2
    @EXIT /B 1
) ELSE IF %%~zF EQU 0 (
    @ECHO Error: failed to download %_INSTALLER_TYPE% (file empty) 1>&2
    @EXIT /B 1
)
:DOWNLOADED

:: installing conda
@ECHO Installing %_INSTALLER_TYPE%...
@START /wait "" "%_INSTALLER_FILE%" /InstallationType=JustMe /RegisterPython=0 /AddToPath=0 /S /D=%_DEVENV% > NUL
@IF NOT %ErrorLevel%==0 (
    @ECHO Error: failed to install %_INSTALLER_TYPE% 1>&2
    @EXIT /B 1
)

:: Windows doesn't ship with git so ensure installed into base otherwise auxlib will act up
@CALL :CONDA "%_BASEEXE%" install --yes --quiet --name=base "git" > NUL
:INSTALLED

:: create empty env if it doesn't exist
@IF EXIST "%_ENV%" @GOTO :ENVEXISTS
@ECHO Creating %_NAME%...

@CALL :CONDA "%_BASEEXE%" create --yes --quiet "--prefix=%_ENV%" > NUL
@IF NOT %ErrorLevel%==0 (
    @ECHO Error: failed to create %_NAME% 1>&2
    @EXIT /B 1
)
:ENVEXISTS

:: check if explicitly updating or if 24 hrs since last update
@CALL :UPDATING
@IF NOT %ErrorLevel%==0 @GOTO :UP_TO_DATE
@ECHO Updating %_INSTALLER_TYPE%...

@CALL :CONDA "%_BASEEXE%" update --yes --quiet --all "--prefix=%_ENV%" > NUL
@IF NOT %ErrorLevel%==0 (
    @ECHO Error: failed to update %_INSTALLER_TYPE% 1>&2
    @EXIT /B 1
)

@ECHO Updating %_NAME%...

:: set channels based on installer type
@IF "%_INSTALLER_TYPE%"=="miniconda" (
    @SET "_CHANNEL_NAME=defaults"
) ELSE (
    @SET "_CHANNEL_NAME=conda-forge"
)

@CALL :CONDA "%_BASEEXE%" install ^
    --yes ^
    --quiet ^
    "--prefix=%_ENV%" ^
    --override-channels ^
    "--channel=%_CHANNEL_NAME%" ^
    "--file=%_SRC%\tests\requirements.txt" ^
    "--file=%_SRC%\tests\requirements-ci.txt" ^
    "--file=%_SRC%\tests\requirements-Windows.txt" ^
    "python=%_PYTHON%" > NUL
@IF NOT %ErrorLevel%==0 (
    @ECHO Error: failed to update %_NAME% 1>&2
    @EXIT /B 1
)

:: update timestamp
@IF EXIST "%_UPDATED%" @DEL "%_UPDATED%"
@ECHO > "%_UPDATED%"
:UP_TO_DATE

:: "install" conda
:: trick conda into importing from our source code and not from site-packages
@IF "%PYTHONPATH%"=="" (
    @SET "PYTHONPATH=%_SRC%"
) ELSE (
    @SET "PYTHONPATH=%_SRC%;%PYTHONPATH%"
)

:: copy latest shell scripts
@ECHO Updating shell scripts...
@CALL :CONDA "%_ENVEXE%" init --install > NUL
@IF NOT %ErrorLevel%==0 (
    @ECHO Error: failed to update shell scripts 1>&2
    @EXIT /B 1
)

:: initialize conda command
@ECHO Initializing shell integration...
@SET "CONDA_AUTO_ACTIVATE=0"
@CALL "%_CONDAHOOK%"
@SET CONDA_AUTO_ACTIVATE=
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
:: Only set DOSKEY alias if running in Command Prompt (not PowerShell)
@WHERE DOSKEY > NUL 2>&1
@IF %ErrorLevel%==0 (
    @DOSKEY conda="%CONDA_BAT%" $*
)

:CLEANUP
@SET _ARG=
@SET _BASEEXE=
@SET _CHANNEL_NAME=
@SET _CONDABAT=
@SET _DEVENV=
@SET _DOWNLOAD_URL=
@SET _DRYRUN=
@SET _ENV=
@SET _ENVEXE=
@SET _INSTALLER=
@SET _INSTALLER_FILE=
@SET _INSTALLER_INITIAL=
@SET _INSTALLER_TYPE=
@SET _NAME=
@SET _PATH=
@SET _PYTHON=
@SET _PYTHONEXE=
@SET _SCRIPT=
@SET _SRC=
@SET _UPDATE=
@SET _UPDATED=
@GOTO :RESET_ERRORLEVEL

:RESET_ERRORLEVEL
@EXIT /B 0

:CONDA *args
:: include OpenSSL & git on %PATH%
@SET "_PATH=%PATH%"
@SET "PATH=%1\..\..\Library\bin;%PATH%"

@CALL %*
@IF NOT %ErrorLevel%==0 @EXIT /B %ErrorLevel%

:: restore %PATH%
@SET "PATH=%_PATH%"
@SET _PATH=
@GOTO :EOF

:DEVENV_CONDARC
:: read devenv from ~\.condarc
:: check if ~\.condarc exists
@IF NOT EXIST "%USERPROFILE%\.condarc" @EXIT /B 0
:: check if devenv key is defined
@FINDSTR /R /C:"^devenv:" "%USERPROFILE%\.condarc" > NUL
@IF NOT %ErrorLevel%==0 @EXIT /B 0
:: read devenv key (with path expansion)
@FOR /F "usebackq delims=" %%I IN (`powershell.exe -NoProfile -Command "(Select-String -Path '~\.condarc' -Pattern '^devenv:\s*(.+)' | Select-Object -Last 1).Matches.Groups[1].Value -replace '^~',""$Env:UserProfile"""`) DO @SET "_DEVENV=%%~fI"
@GOTO :EOF

:INSTALLER_TYPE_CONDARC
:: read installer_type from ~\.condarc
:: check if ~\.condarc exists
@IF NOT EXIST "%USERPROFILE%\.condarc" @EXIT /B 0
:: check if installer_type key is defined
@FINDSTR /R /C:"^installer_type:" "%USERPROFILE%\.condarc" > NUL
@IF NOT %ErrorLevel%==0 @EXIT /B 0
:: read installer_type key
@FOR /F "usebackq delims=" %%I IN (`powershell.exe -NoProfile -Command "(Select-String -Path '~\.condarc' -Pattern '^installer_type:\s*(.+)' | Select-Object -Last 1).Matches.Groups[1].Value"`) DO @SET "_INSTALLER_TYPE=%%I"
@GOTO :EOF

:UPDATING
:: check if explicitly updating or if 24 hrs since last update
@IF %_UPDATE%==0 @EXIT /B 0
@IF NOT EXIST "%_UPDATED%" @EXIT /B 0
@powershell.exe -NoProfile -Command "Exit (Get-Item '"%_UPDATED%"').LastWriteTime -ge (Get-Date).AddHours(-24)"
@EXIT /B %ErrorLevel%

:DRYRUN
:: dry-run printout
@ECHO Python: %_PYTHON%
@IF EXIST "%_INSTALLER_FILE%" (
    @ECHO Installer [%_INSTALLER_TYPE%]: %_INSTALLER_FILE% [exists]
) ELSE (
    @ECHO Installer [%_INSTALLER_TYPE%]: %_INSTALLER_FILE% [pending]
)
@IF EXIST "%_DEVENV%" (
    @ECHO Devenv: %_DEVENV% [exists]
) ELSE (
    @ECHO Devenv: %_DEVENV% [pending]
)
@CALL :UPDATING
@IF %ErrorLevel%==0 (
    @ECHO Updating: [yes]
) ELSE (
    @ECHO Updating: [no]
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
