@REM Copyright (C) 2012 Anaconda, Inc
@REM SPDX-License-Identifier: BSD-3-Clause
@IF EXIST "%~dp0..\Scripts\conda.exe" @SET "CONDA_EXE=%~dp0..\Scripts\conda.exe"
@IF "%CONDA_EXE%" == "" (
  @ECHO CONDA_EXE env var is unset, and conda.exe could not be located by relative path.  exiting.
  EXIT 1
)

@IF [%1]==[activate]   "%~dp0_conda_activate" %*
@IF [%1]==[deactivate] "%~dp0_conda_activate" %*

@SETLOCAL
@FOR %%A IN ("%~dp0\.") DO @SET _sysp=%%~dpA
@SET _sysp=%_sysp:~0,-1%
@FOR %%B in (%~dp0.) DO @SET PATH=%_sysp%;%_sysp%\Library\mingw-w64\bin;%_sysp%\Library\usr\bin;%_sysp%\Library\bin;%_sysp%\Scripts;%_sysp%\bin;%PATH%
CALL "%CONDA_EXE%" %*
@ENDLOCAL

@IF %errorlevel% NEQ 0 EXIT /B %errorlevel%

@IF [%1]==[install]   "%~dp0_conda_activate" reactivate
@IF [%1]==[update]    "%~dp0_conda_activate" reactivate
@IF [%1]==[upgrade]   "%~dp0_conda_activate" reactivate
@IF [%1]==[remove]    "%~dp0_conda_activate" reactivate
@IF [%1]==[uninstall] "%~dp0_conda_activate" reactivate
