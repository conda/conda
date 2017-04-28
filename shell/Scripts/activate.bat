@REM @ symbols in this file indicate that output should not be printed.
@REM   Setting it this way allows us to not touch the user's echo setting.
@REM   For debugging, remove the @ on the section you need to study.
@setlocal enabledelayedexpansion
@FOR /F "delims=" %%i IN ('@"%~dp0..\python.exe" -c "import ctypes; print(ctypes.cdll.kernel32.GetACP())"') DO @SET "PYTHONIOENCODING=%%i"
@chcp !PYTHONIOENCODING! > NUL
@endlocal

@set "_CONDA_NEW_ENV=%~1"

@if "%~2" == "" @goto skiptoomanyargs
    (@echo Error: activate only accepts a single argument.) 1>&2
    (@echo     ^(Got %*^)) 1>&2
    @exit /b 1
:skiptoomanyargs

@if not "%~1" == "" @goto skipmissingarg
    @REM Set env to root if no arg provided
    @set _CONDA_NEW_ENV=root
:skipmissingarg


@SET "_CONDA_BAT=%~dp0..\Library\bin\conda.bat"

@CALL %_CONDA_BAT% activate "%_CONDA_NEW_ENV%"

@SET _CONDA_BAT=
