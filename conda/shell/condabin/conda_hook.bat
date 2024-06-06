:: Copyright (C) 2012 Anaconda, Inc
:: SPDX-License-Identifier: BSD-3-Clause
:: The file name is conda_hook.bat rather than conda-hook.bat because conda will see
:: the latter as a 'conda hook' command.

:: disable displaying the command before execution
@ECHO OFF

:: check if conda DOSKEY is already defined
(DOSKEY /MACROS | FINDSTR /R /C:"^conda=" >NUL 2>NUL) && GOTO :EOF

:: enter localized variable scope
SETLOCAL

:: get root & condabin
FOR %%P IN ("%~dp0\..") DO SET "__condaroot=%%~fP"
SET __condabin=%__condaroot%\condabin

:: set conda alias
DOSKEY conda="%__condabin%\conda.bat" $*

:: exit localized variable scope
ENDLOCAL & (
    SET "PATH=%__condabin%;%PATH%"
    SET "CONDA_EXE=%__condaroot%\Scripts\conda.exe"
    SET _CE_M=
    SET _CE_CONDA=
    SET CONDA_SHLVL=0
)
