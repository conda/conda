:: Copyright (C) 2012 Anaconda, Inc
:: SPDX-License-Identifier: BSD-3-Clause
:: Helper routine for activation, deactivation, and reactivation.

:: disable displaying the command before execution
@ECHO OFF

IF DEFINED CONDA_PS1_BACKUP (
    :: Handle transition from shell activated with conda 4.3 to a subsequent activation
    :: after conda updated to 4.4. See issue #6173.
    SET "PROMPT=%CONDA_PS1_BACKUP%"
    SET CONDA_PS1_BACKUP=
)

:: attempt to find a unique temporary directory to use
FOR %%A IN ("%TMP%") DO SET TMP=%%~sA
SET _I=100
:CREATE
IF [%_I%]==[0] (
    ECHO Failed to create temp directory "%TMP%\conda-<RANDOM>\" 1>&2
    SET _I=
    EXIT /B 1
)
SET /A _I-=1
SET "UNIQUE_DIR=%TMP%\conda-%RANDOM%"
MKDIR "%UNIQUE_DIR%" >NUL 2>NUL || GOTO :CREATE
SET _I=

:: found a unique directory
SET "UNIQUE=%UNIQUE_DIR%\conda.tmp"
TYPE NUL >%UNIQUE%

:: call conda
("%CONDA_EXE%" %_CE_M% %_CE_CONDA% shell.cmd.exe %* 1>%UNIQUE%) || EXIT /B 1

:: get temporary script to run
FOR /F %%i IN (%UNIQUE%) DO SET _TEMP_SCRIPT_PATH=%%i
RMDIR /S /Q %UNIQUE_DIR%
FOR /F "delims=" %%A IN ("%_TEMP_SCRIPT_PATH%") DO ENDLOCAL & SET _TEMP_SCRIPT_PATH=%%~A
IF NOT DEFINED _TEMP_SCRIPT_PATH EXIT /B 1

:: call temporary script
IF DEFINED CONDA_PROMPT_MODIFIER CALL SET "PROMPT=%%PROMPT:%CONDA_PROMPT_MODIFIER%=%%"
CALL "%_TEMP_SCRIPT_PATH%" || EXIT /B 1
SET "PROMPT=%CONDA_PROMPT_MODIFIER%%PROMPT%"

:: cleanup
IF DEFINED CONDA_TEST_SAVE_TEMPS ECHO CONDA_TEST_SAVE_TEMPS :: retaining activate_batch %_TEMP_SCRIPT_PATH% 1>&2
IF NOT DEFINED CONDA_TEST_SAVE_TEMPS DEL /F /Q "%_TEMP_SCRIPT_PATH%"
SET _TEMP_SCRIPT_PATH=
