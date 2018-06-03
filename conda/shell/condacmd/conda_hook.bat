@REM Copyright (C) 2012 Anaconda, Inc
@REM SPDX-License-Identifier: BSD-3-Clause
@REM The file name is conda_hook.bat rather than conda-hook.bat because conda will see
@REM the latter as a 'conda hook' command.

@IF DEFINED CONDA_BAT GOTO :EOF

@FOR %%F in ("%~dp0") do @SET __condacmd_dir=%%~dpF
@SET "PATH=%__condacmd_dir%;%PATH%"
@SET CONDA_BAT="%__condacmd_dir%conda.bat"
@SET __condacmd_dir=%__condacmd_dir:~0,-1%
@FOR %%F in ("%__condacmd_dir%") do @SET __conda_root=%%~dpF
@SET CONDA_EXE="%__conda_root%Scripts\conda.exe"
@SET __condacmd_dir=
@SET __conda_root=

@DOSKEY conda=%CONDA_BAT% $*

@IF DEFINED CONDA_SHLVL GOTO :EOF
@SET CONDA_SHLVL=0
