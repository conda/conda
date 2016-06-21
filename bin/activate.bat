@REM @ symbols in this file indicate that output should not be printed.
@REM   Setting it this way allows us to not touch the user's echo setting.
@REM   For debugging, remove the @ on the section you need to study.
@setlocal enabledelayedexpansion

@set "CONDA_NEW_ENV=%~1"

:: this finds either --help or -h and shows the help text
@CALL ECHO "%~1"| @%SystemRoot%\System32\find.exe /I "-h" 1>NUL
@IF NOT ERRORLEVEL 1 (
    @call "%~dp0\..\Scripts\conda.exe" ..activate "cmd.exe" -h
) else (
    :: reset errorlevel to 0
    cmd /c "exit /b 0"
)

@if "%~2" == "" @goto skiptoomanyargs
    (@echo Error: did not expect more than one argument.) 1>&2
    (@echo     ^(Got %*^)) 1>&2
    @exit /b 1
:skiptoomanyargs

@if not "%~1" == "" @goto skipmissingarg
    @REM Set env to root if no arg provided
    @set CONDA_NEW_ENV=root
:skipmissingarg

@SET "CONDA_EXE=%~dp0\..\Scripts\conda.exe"

@REM Ensure that path or name passed is valid before deactivating anything
@CALL "%CONDA_EXE%" ..checkenv "cmd.exe" "%CONDA_NEW_ENV%"
@IF errorlevel 1 exit /b 1

@call "%~dp0\deactivate.bat"
@if errorlevel 1 exit /b 1

@REM take a snapshot of pristine state for later
@SET "CONDA_PATH_BACKUP=%PATH%"
@REM Activate the new environment
@FOR /F "delims=" %%i IN ('@call "%CONDA_EXE%" ..activate "cmd.exe" "%CONDA_NEW_ENV%"') DO @SET "NEW_PATH=%%i"

@REM take a snapshot of pristine state for later
@SET "CONDA_PS1_BACKUP=%PROMPT%"
@FOR /F "delims=" %%i IN ('@call "%CONDA_EXE%" ..changeps1') DO @SET "CHANGE_PROMPT=%%i"

:: if our prompt var does not contain reference to CONDA_DEFAULT_ENV, set prompt
@IF "%CHANGE_PROMPT%" == "1" @IF "x%PROMPT:CONDA_DEFAULT_ENV=%" == "x%PROMPT%" (
    SET "PROMPT=(%CONDA_NEW_ENV%) %PROMPT%"
)

@REM This persists env variables, which are otherwise local to this script right now.
@endlocal & (
    @REM Used for deactivate, to make sure we restore original state after deactivation
    @SET "CONDA_PATH_BACKUP=%CONDA_PATH_BACKUP%"
    @SET "CONDA_PS1_BACKUP=%CONDA_PS1_BACKUP%"
    @SET "PROMPT=%PROMPT%"
    @SET "PATH=%NEW_PATH%;%PATH%"
    @SET "CONDA_DEFAULT_ENV=%CONDA_NEW_ENV%"

    @REM Run any activate scripts
    @IF EXIST "%CONDA_NEW_ENV%\etc\conda\activate.d" (
        @PUSHD "%CONDA_NEW_ENV%\etc\conda\activate.d"
        @FOR %%g in (*.bat) DO @CALL "%%g"
        @POPD
    )
)
