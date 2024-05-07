:: Copyright (C) 2012 Anaconda, Inc
:: SPDX-License-Identifier: BSD-3-Clause

:: disable displaying the command before execution
@ECHO OFF

ECHO DeprecationWarning: 'deactivate' is deprecated. Use 'conda deactivate'. 1>&2

:: invoke conda
CALL "%~dp0\conda.bat" deactivate %*
