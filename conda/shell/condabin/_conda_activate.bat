@REM Copyright (C) 2012 Anaconda, Inc
@REM SPDX-License-Identifier: BSD-3-Clause
@REM Helper routine for activation, deactivation, and reactivation.

@IF "%CONDA_PS1_BACKUP%"=="" GOTO FIXUP43
    @REM Handle transition from shell activated with conda 4.3 to a subsequent activation
    @REM after conda updated to 4.4. See issue #6173.
    @SET "PROMPT=%CONDA_PS1_BACKUP%"
    @SET CONDA_PS1_BACKUP=
:FIXUP43

@SETLOCAL EnableDelayedExpansion
@IF DEFINED _CE_CONDA (
  @REM when _CE_CONDA is defined, we're in develop mode.  CONDA_EXE is actually python.exe in the root of the dev env.
  FOR %%A IN ("%CONDA_EXE%") DO @SET _sysp=%%~dpA
) ELSE (
  @REM This is the standard user case.  This script is run in root\condabin.
  FOR %%A IN ("%~dp0.") DO @SET _sysp=%%~dpA
  IF NOT EXIST "!_sysp!\Scripts\conda.exe" @SET "_sysp=!_sysp!..\"
)
@SET _sysp=!_sysp:~0,-1!
@SET PATH=!_sysp!;!_sysp!\Library\mingw-w64\bin;!_sysp!\Library\usr\bin;!_sysp!\Library\bin;!_sysp!\Scripts;!_sysp!\bin;%PATH%
@REM It seems that it is not possible to have "CONDA_EXE=Something With Spaces"
@REM and %* to contain: activate "Something With Spaces does not exist".
@REM MSDOS associates the outer "'s and is unable to run very much at all.
@REM @SET CONDA_EXES="%CONDA_EXE%" %_CE_M% %_CE_CONDA%
@REM @FOR /F %%i IN ('%CONDA_EXES% shell.cmd.exe %*') DO @SET _TEMP_SCRIPT_PATH=%%i not return error
@REM This method will not work if %TMP% contains any spaces.
:tmpName
@SET UNIQUE=%TMP%\conda-%RANDOM%-%RANDOM%.tmp
@IF EXIST "%UNIQUE%" goto :tmpName
@TYPE NUL 1>%UNIQUE%
@"%CONDA_EXE%" %_CE_M% %_CE_CONDA% shell.cmd.exe %* 1>%UNIQUE%
@IF %ErrorLevel% NEQ 0 @EXIT /B %ErrorLevel%
@FOR /F %%i IN (%UNIQUE%) DO @SET _TEMP_SCRIPT_PATH=%%i
@DEL /F /Q "%UNIQUE%"
@FOR /F "delims=" %%A in (""!_TEMP_SCRIPT_PATH!"") DO @ENDLOCAL & @SET _TEMP_SCRIPT_PATH=%%~A
@IF "%_TEMP_SCRIPT_PATH%" == "" @EXIT /B 1
@IF NOT "%CONDA_PROMPT_MODIFIER%" == "" @CALL SET "PROMPT=%%PROMPT:%CONDA_PROMPT_MODIFIER%=%_empty_not_set_%%%"
@CALL "%_TEMP_SCRIPT_PATH%"
@IF NOT "%CONDA_TEST_SAVE_TEMPS%x"=="x" @ECHO CONDA_TEST_SAVE_TEMPS :: retaining activate_batch %_TEMP_SCRIPT_PATH% 1>&2
@IF "%CONDA_TEST_SAVE_TEMPS%x"=="x" @DEL /F /Q "%_TEMP_SCRIPT_PATH%"
@SET _TEMP_SCRIPT_PATH=
@SET "PROMPT=%CONDA_PROMPT_MODIFIER%%PROMPT%"
