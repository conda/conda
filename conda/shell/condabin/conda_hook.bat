:: Copyright (C) 2012 Anaconda, Inc
:: SPDX-License-Identifier: BSD-3-Clause
:: The file name is conda_hook.bat rather than conda-hook.bat because conda will see
:: the latter as a 'conda hook' command.

:: disable displaying the command before execution
@ECHO OFF

:: check if conda DOSKEY is already defined
(DOSKEY /MACROS | FINDSTR /R /C:"^conda=" >NUL 2>NUL) && GOTO :EOF

:: get root & condabin
FOR %%P IN ("%~dp0\..") DO SET "__condaroot=%%~fP"
SET __condabin=%__condaroot%\condabin

:: set PATH, CONDA_BAT, CONDA_EXE
SET "PATH=%__condabin%;%PATH%"
SET "CONDA_BAT=%__condabin%\conda.bat"
SET "CONDA_EXE=%__condaroot%\Scripts\conda.exe"
SET _CE_M=
SET _CE_CONDA=

:: set conda alias
DOSKEY conda="%CONDA_BAT%" $*
SET CONDA_SHLVL=0

: cleanup
SET __condabin=
SET __condaroot=
