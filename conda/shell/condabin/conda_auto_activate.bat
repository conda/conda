:: Copyright (C) 2012 Anaconda, Inc
:: SPDX-License-Identifier: BSD-3-Clause
:: Helper script to conda_hook.bat.  This is a separate script so that the Anaconda Prompt
:: can enable this option while only conda_hook.bat can be used in AutoRun.

:: disable displaying the command before execution
@ECHO OFF

:: initialize conda
CALL "%~dp0\conda_hook.bat"

:: enter localized variable scope (won't need to unset temporary variables)
SETLOCAL

:: conditionally activate base environment
FOR /F "delims=" %%I IN ('CALL conda config --show auto_activate_base') DO SET "__conda_auto_activate_base=%%I"
IF NOT [%__conda_auto_activate_base:True=%]==[%__conda_auto_activate_base%] ENDLOCAL & CALL conda activate base
