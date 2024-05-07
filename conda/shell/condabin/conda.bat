:: Copyright (C) 2012 Anaconda, Inc
:: SPDX-License-Identifier: BSD-3-Clause

:: disable displaying the command before execution
@ECHO OFF

:: enter localized variable scope and delay variable expansion until runtime
SETLOCAL EnableDelayedExpansion

IF NOT DEFINED CONDA_EXE (
    FOR %%P IN ("%~dp0\..") DO SET "__condaroot=%%~fP"
    SET "CONDA_EXE=%__condaroot%\Scripts\conda.exe"
    SET _CE_M=
    SET _CE_CONDA=
)

:: exit localized variable scope
ENDLOCAL & (
    SET "CONDA_EXE=%CONDA_EXE%"
    SET "_CE_M=%_CE_M%"
    SET "_CE_CONDA=%_CE_CONDA%"
)

:: "source" _conda_activate.bat script, we do not return from this script
IF [%1]==[activate]   "%~dp0\_conda_activate.bat" %*
IF [%1]==[deactivate] "%~dp0\_conda_activate.bat" %*

:: call conda subroutine
(CALL "%CONDA_EXE%" %_CE_M% %_CE_CONDA% %*) || EXIT /B %ERRORLEVEL%

:: "source" _conda_activate.bat script, we do not return from this script
IF [%1]==[install]   "%~dp0\_conda_activate.bat" reactivate
IF [%1]==[update]    "%~dp0\_conda_activate.bat" reactivate
IF [%1]==[upgrade]   "%~dp0\_conda_activate.bat" reactivate
IF [%1]==[remove]    "%~dp0\_conda_activate.bat" reactivate
IF [%1]==[uninstall] "%~dp0\_conda_activate.bat" reactivate
