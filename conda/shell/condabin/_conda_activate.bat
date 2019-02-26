@REM Copyright (C) 2012 Anaconda, Inc
@REM SPDX-License-Identifier: BSD-3-Clause
@REM Helper routine for activation, deactivation, and reactivation.

@IF "%CONDA_PS1_BACKUP%"=="" GOTO FIXUP43
    @REM Handle transition from shell activated with conda 4.3 to a subsequent activation
    @REM after conda updated to 4.4. See issue #6173.
    @SET "PROMPT=%CONDA_PS1_BACKUP%"
    @SET CONDA_PS1_BACKUP=
:FIXUP43

@SETLOCAL enabledelayedexpansion
@FOR %%A in ("%~dp0\.") DO @SET _sysp=%%~dpA
@SET _sysp=%_sysp:~0,-1%
@FOR %%B in (%~dp0.) DO @SET PATH=%_sysp%;%_sysp%\Library\mingw-w64\bin;%_sysp%\Library\usr\bin;%_sysp%\Library\bin;%_sysp%\Scripts;%_sysp%\bin;%PATH%
@FOR /F "delims=" %%i IN ('@CALL "%CONDA_EXE%" shell.cmd.exe %*') DO @SET "_TEMP_SCRIPT_PATH=%%i"
@ENDLOCAL & @SET "_TEMP_SCRIPT_PATH=%_TEMP_SCRIPT_PATH%"
@IF "%_TEMP_SCRIPT_PATH%"=="" @EXIT /B 1
@IF NOT "%CONDA_PROMPT_MODIFIER%" == "" @CALL SET "PROMPT=%%PROMPT:%CONDA_PROMPT_MODIFIER%=%_empty_not_set_%%%"
@CALL "%_TEMP_SCRIPT_PATH%"
@DEL /F /Q "%_TEMP_SCRIPT_PATH%"
@SET _TEMP_SCRIPT_PATH=
@SET "PROMPT=%CONDA_PROMPT_MODIFIER%%PROMPT%"
@REM We do not unconditionally remove the first two characters as PYTHONIOENCODING could
@REM be set to just a number (old conda, other tooling).
@IF DEFINED PYTHONIOENCODING chcp %PYTHONIOENCODING:cp=% > NUL
