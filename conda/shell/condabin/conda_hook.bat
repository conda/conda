:: Copyright (C) 2012 Anaconda, Inc
:: SPDX-License-Identifier: BSD-3-Clause
:: The file name is conda_hook.bat rather than conda-hook.bat because conda will see
:: the latter as a 'conda hook' command.

@IF DEFINED CONDA_SHLVL GOTO :EOF

:: get root & condabin
@FOR %%P IN ("%~dp0\..") DO @SET "__condaroot=%%~fP"
@SET __condabin=%__condaroot%\condabin

:: set PATH, CONDA_BAT, CONDA_EXE
@SET "PATH=%__condabin%;%PATH%"
@SET "CONDA_BAT=%__condabin%\conda.bat"
@SET "CONDA_EXE=%__condaroot%\Scripts\conda.exe"

:: set conda alias
@DOSKEY conda="%CONDA_BAT%" $*
@SET CONDA_SHLVL=0

:CLEANUP
@SET __condabin=
@SET __condaroot=
