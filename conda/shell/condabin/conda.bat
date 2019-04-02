@REM Copyright (C) 2012 Anaconda, Inc
@REM SPDX-License-Identifier: BSD-3-Clause

@REM echo _CE_CONDA is %_CE_CONDA%
@REM echo _CE_M is %_CE_M%
@REM echo CONDA_EXE is %CONDA_EXE%

@IF DEFINED _CE_CONDA (
  FOR %%A IN ("%CONDA_EXE%") DO @SET "_sysp=%%~dpA."
) else (
  @SET "_sysp=%~dp0..\"
  @SET _CE_M=
  @SET _CE_CONDA=
  @SET "CONDA_EXE=%~dp0..\Scripts\conda.exe"
)
@IF [%1]==[activate]   "%~dp0_conda_activate" %*
@IF [%1]==[deactivate] "%~dp0_conda_activate" %*

@SETLOCAL
@SET "_sysp=%_sysp:~0,-1%"
@SET "PATH=%_sysp%;%_sysp%\Library\mingw-w64\bin;%_sysp%\Library\usr\bin;%_sysp%\Library\bin;%_sysp%\Scripts;%_sysp%\bin;%PATH%"
@SET CONDA_EXES="%CONDA_EXE%" %_CE_M% %_CE_CONDA%
@CALL %CONDA_EXES% %*
@ENDLOCAL

@IF %errorlevel% NEQ 0 EXIT /B %errorlevel%

@IF [%1]==[install]   "%~dp0_conda_activate" reactivate
@IF [%1]==[update]    "%~dp0_conda_activate" reactivate
@IF [%1]==[upgrade]   "%~dp0_conda_activate" reactivate
@IF [%1]==[remove]    "%~dp0_conda_activate" reactivate
@IF [%1]==[uninstall] "%~dp0_conda_activate" reactivate
