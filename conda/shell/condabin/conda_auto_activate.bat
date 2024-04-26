:: Copyright (C) 2012 Anaconda, Inc
:: SPDX-License-Identifier: BSD-3-Clause
:: Helper script to conda_hook.bat.  This is a separate script so that the Anaconda Prompt
:: can enable this option while only conda_hook.bat can be used in AutoRun.

:: disable displaying the command before execution
@ECHO OFF

:: get auto_activate_base value
FOR /F "delims=" %%I IN ('CALL "%CONDA_EXE%" config --show auto_activate_base') DO SET "__conda_auto_activate_base=%%I"

:: conditionally activate base environment
IF NOT [%__conda_auto_activate_base:True=%]==[%__conda_auto_activate_base%] CALL "%CONDA_BAT%" activate base

:: cleanup
SET __conda_auto_activate_base=
