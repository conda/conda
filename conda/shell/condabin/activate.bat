:: Copyright (C) 2012 Anaconda, Inc
:: SPDX-License-Identifier: BSD-3-Clause

:: disable displaying the command before execution
@ECHO OFF

:: invoke conda
CALL "%~dp0\conda.bat" activate %*
