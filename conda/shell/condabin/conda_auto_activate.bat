:: Copyright (C) 2012 Anaconda, Inc
:: SPDX-License-Identifier: BSD-3-Clause
:: Helper script to conda_hook.bat.  This is a separate script so that the Anaconda Prompt
:: can enable this option while only conda_hook.bat can be used in AutoRun.

@FOR /F "delims=" %%i IN ('@CALL "%CONDA_EXE%" config --show auto_activate') DO @SET "__conda_auto_activate=%%i"
@FOR /F "delims=" %%i IN ('@CALL "%CONDA_EXE%" config --show default_activation_env') DO @SET "__conda_auto_activate_name=%%i"
@IF NOT "x%__conda_auto_activate:True=%"=="x%__conda_auto_activate%" @CALL "%CONDA_BAT%" activate "%__conda_auto_activate_name:default_activation_env: =%"
@SET "__conda_auto_activate="
@SET "__conda_auto_activate_name="
