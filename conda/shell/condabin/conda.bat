:: Copyright (C) 2012 Anaconda, Inc
:: SPDX-License-Identifier: BSD-3-Clause

@IF NOT DEFINED CONDA_EXE (
  @FOR %%P IN ("%~dp0\..") DO @SET "__condaroot=%%~fP"
  @SET "CONDA_EXE=%__condaroot%\Scripts\conda.exe"
  @SET _CE_M=
  @SET _CE_CONDA=
  @SET __condaroot=
)
@IF [%1]==[activate]   "%~dp0\_conda_activate.bat" %*
@IF [%1]==[deactivate] "%~dp0\_conda_activate.bat" %*

@CALL "%CONDA_EXE%" %_CE_M% %_CE_CONDA% %*
@IF NOT [%ERRORLEVEL%]==[0] EXIT /B %ERRORLEVEL%

@IF [%1]==[install]   "%~dp0\_conda_activate.bat" reactivate
@IF [%1]==[update]    "%~dp0\_conda_activate.bat" reactivate
@IF [%1]==[upgrade]   "%~dp0\_conda_activate.bat" reactivate
@IF [%1]==[remove]    "%~dp0\_conda_activate.bat" reactivate
@IF [%1]==[uninstall] "%~dp0\_conda_activate.bat" reactivate

@EXIT /B %ERRORLEVEL%
