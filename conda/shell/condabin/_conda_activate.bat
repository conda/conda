@REM Copyright (C) 2012 Anaconda, Inc
@REM SPDX-License-Identifier: BSD-3-Clause
@REM Helper routine for activation, deactivation, and reactivation.

@ECHO ON

@IF DEFINED _CE_CONDA (
  FOR %%A IN ("%CONDA_EXE%") DO @SET "_sysp=%%~dpA."
) ELSE (
  @SET _sysp="%~dp0"
)

@IF "%CONDA_PS1_BACKUP%"=="" GOTO FIXUP43
    @REM Handle transition from shell activated with conda 4.3 to a subsequent activation
    @REM after conda updated to 4.4. See issue #6173.
    @SET "PROMPT=%CONDA_PS1_BACKUP%"
    @SET CONDA_PS1_BACKUP=
:FIXUP43

SET _TEMP_SCRIPT_PATH_2=
@SETLOCAL EnableDelayedExpansion
@SET _sysp=%_sysp:~0,-1%
SET PATH=%_sysp%;%_sysp%\Library\mingw-w64\bin;%_sysp%\Library\usr\bin;%_sysp%\Library\bin;%_sysp%\Scripts;%_sysp%\bin;%PATH%
FOR /F %%i IN ('"!CONDA_EXE!" !_CE_M! !_CE_CONDA! shell.cmd.exe %*') DO @SET "_TEMP_SCRIPT_PATH=%%i"
@FOR /F "delims=" %%A in (""!_TEMP_SCRIPT_PATH!"") DO @ENDLOCAL & @SET "_TEMP_SCRIPT_PATH_2=%%~A"
@SETLOCAL EnableDelayedExpansion
IF "%_TEMP_SCRIPT_PATH_2%" == "" @EXIT /B 1
@endlocal
echo hai CONDA_PROMPT_MODIFIER=!CONDA_PROMPT_MODIFIER! CONDA_PROMPT_MODIFIER=%CONDA_PROMPT_MODIFIER%
@IF NOT "%CONDA_PROMPT_MODIFIER%" == "" @CALL SET "PROMPT=%%PROMPT:%CONDA_PROMPT_MODIFIER%=%_empty_not_set_%%%"
echo hai2 CONDA_PROMPT_MODIFIER=!CONDA_PROMPT_MODIFIER! CONDA_PROMPT_MODIFIER=%CONDA_PROMPT_MODIFIER%
@CALL "%_TEMP_SCRIPT_PATH_2%"
echo hai3
@IF "%_TEMP_SCRIPT_PATH_2%x"=="x" @DEL /F /Q "%_TEMP_SCRIPT_PATH_2%"
@IF NOT "%CONDA_TEST_SAVE_TEMPS%x"=="x" @ECHO SAVED TEMPS TO "%_TEMP_SCRIPT_PATH_2%"
@SET _TEMP_SCRIPT_PATH_2=
@SET "PROMPT=%CONDA_PROMPT_MODIFIER%%PROMPT%"
