:: Copyright (C) 2012 Anaconda, Inc
:: SPDX-License-Identifier: BSD-3-Clause

:: disable displaying the command before execution
@ECHO OFF

CALL "%~dp0\..\..\condabin\conda.bat" %*
