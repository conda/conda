:: Copyright (C) 2012 Anaconda, Inc
:: SPDX-License-Identifier: BSD-3-Clause

@ECHO DeprecationWarning: 'activate' is deprecated. Use 'conda activate'. 1>&2
@CALL "%~dp0\conda_hook.bat"
conda activate %*
