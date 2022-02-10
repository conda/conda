@REM parse args
:ARGS_LOOP
@IF "%~1"=="" @GOTO :ARGS_END

@REM convert to uppercase
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

@IF "%_ARG%"=="/?" (
    @ECHO Usage: %~0 [/P VERSION] [/U] [/D PATH] [/?]
    @ECHO.
    @ECHO Options:
    @ECHO   /P  PYTHON  Specify the Python version for the devenv ^(default: 3.8^)
    @ECHO   /U          Force update packages ^(default: update every 24 hours^)
    @ECHO   /D  PATH    Provide the desired devenv path ^(default: devenv\Windows^)
    @ECHO.  /?          Display this
    @EXIT /B 0
)

@ECHO Error: unknown option %~1 1>&2
@EXIT /B 1
:ARGS_END
@IF "%_DEVENV%"=="" @SET "_DEVENV=%CD%\devenv\Windows"
@IF NOT EXIST "%_DEVENV%" @MKDIR "%_DEVENV%"
@IF "%_PYTHON%"=="" @SET "_PYTHON=3.8"
@IF "%_UPDATE%"=="" @SET "_UPDATE=1"

@REM deactivate any prior envs
@IF "%CONDA_SHLVL%"=="" @GOTO DEACTIVATED
@ECHO Deactivating %CONDA_SHLVL% environments...
:DEACTIVATING
@IF "%CONDA_SHLVL%"=="0" @GOTO DEACTIVATED
@CALL conda deactivate
@IF NOT %ErrorLevel%==0 (
    @ECHO Error: failed to deactivate environment 1>&2
    @EXIT /B 1
)
@GOTO DEACTIVATING
:DEACTIVATED

@REM get/set variables
@SET "_STUB=devenv-%_PYTHON%"
@SET "_ENV=%_DEVENV%\envs\%_STUB%"
@SET "_UPDATED=%_ENV%\.devenv-updated"
@SET "_CONDA_EXE=%_DEVENV%\Scripts\conda.exe"
@SET "_ENV_EXE=%_ENV%\Scripts\conda.exe"
@SET "_CONDA_BAT=%_ENV%\condabin\conda.bat"

@REM does conda install exist?
@IF EXIST "%_DEVENV%\conda-meta\history" @GOTO INSTALLED

@REM downloading conda
@IF EXIST "%_DEVENV%\miniconda.exe" @GOTO DOWNLOADED
@ECHO Downloading conda...
@powershell.exe -Command "Invoke-WebRequest -Uri 'https://repo.anaconda.com/miniconda/Miniconda3-latest-Windows-x86_64.exe' -OutFile '%_DEVENV%\miniconda.exe' | Out-Null"
@IF NOT %ErrorLevel%==0 (
    @ECHO Error: failed to download conda 1>&2
    @EXIT /B 1
)
:DOWNLOADED

@REM installing conda
@ECHO Installing conda...
@START /wait "" "%_DEVENV%\miniconda.exe" /InstallationType=JustMe /RegisterPython=0 /AddToPath=0 /S /D=%_DEVENV% > NUL
@IF NOT %ErrorLevel%==0 (
    @ECHO Error: failed to install conda 1>&2
    @EXIT /B 1
)
@REM Windows doesn't ship with git so ensure installed into base
@CALL :CONDA install -yq --name base defaults::git > NUL
:INSTALLED

@REM create empty env if it doesn't exist
@IF EXIST "%_ENV%" @GOTO ENVEXISTS
@ECHO Creating %_STUB%...

@CALL :CONDA create -yq --prefix "%_ENV%" > NUL
@IF NOT %ErrorLevel%==0 (
    @ECHO Error: failed to create %_STUB% 1>&2
    @EXIT /B 1
)
:ENVEXISTS

@REM check if explicitly updating or if 24 hrs since last update
@IF %_UPDATE%==1 (
    @IF EXIST "%_UPDATED%" (
        @powershell.exe -Command "exit (Get-Item "%_UPDATED%").LastWriteTime -lt (Get-Date).AddHours(-24)"
        @IF %ErrorLevel%==0 @GOTO UPTODATE
    )
)
@ECHO Updating %_STUB%...

@CALL :CONDA update -yq --all > NUL
@IF NOT %ErrorLevel%==0 (
    @ECHO Error: failed to update conda 1>&2
    @EXIT /B 1
)

@CALL :CONDA install ^
    -yq ^
    --prefix "%_ENV%" ^
    --override-channels ^
    -c defaults ^
    --file tests\requirements.txt ^
    pywin32 ^
    "python=%_PYTHON%" > NUL
@IF NOT %ErrorLevel%==0 (
    @ECHO Error: failed to update %_STUB% 1>&2
    @EXIT /B 1
)

@REM update timestamp
@IF EXIST "%_UPDATED%" @DEL "%_UPDATED%"
@ECHO > "%_UPDATED%"
:UPTODATE

@REM initialize conda command
@ECHO Initializing conda...
@CALL :CONDA init --dev cmd.exe > NUL
@CALL dev-init.bat > NUL
@IF NOT %ErrorLevel%==0 (
    @ECHO Error: failed to initialize conda 1>&2
    @EXIT /B 1
)
@DEL /Q dev-init.bat

@REM activate dev env
@ECHO Activating %_STUB%...
@CALL conda activate "%_ENV%" > NUL
@IF NOT %ErrorLevel%==0 (
    @ECHO Error: failed to activate %_STUB% 1>&2
    @EXIT /B 1
)
@SET "CONDA_EXE=%_ENV_EXE%"
@SET "CONDA_BAT=%_CONDA_BAT%"
@DOSKEY conda="%CONDA_BAT%" $*

@REM cleanup
@SET _ARG=
@SET _DEVENV=
@SET _PYTHON=
@SET _STUB=
@SET _ENV=
@SET _UPDATED=
@SET _ENV_EXE=
@SET _CONDA_BAT=

@GOTO :EOF

:CONDA *args
@REM include OpenSSL & git on %PATH%
@SET "_PATH=%PATH%"
@SET "PATH=%_DEVENV%\Library\bin;%PATH%"

@CALL "%_CONDA_EXE%" %*
@IF NOT %ErrorLevel%==0 @EXIT /B %ErrorLevel%

@REM restore %PATH%
@SET "PATH=%_PATH%"
@SET _PATH=

@GOTO :EOF
