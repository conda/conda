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

:: enter localized variable scope and delay variable expansion until runtime
SETLOCAL EnableDelayedExpansion

:: attempt to find a unique temporary directory to use
FOR %%P IN ("%TMP%") DO SET TMP=%%~sP
FOR /L %%I IN (1,1,100) DO (
    SET "UNIQUE_DIR=%TMP%\conda-!RANDOM!"
    (MKDIR "!UNIQUE_DIR!" >NUL 2>NUL) && GOTO :CREATED
)
:: failed to create a unique directory, exit without cleanup
ECHO Error: Failed to create temporary directory "%TMP%\conda-<RANDOM>\" 1>&2
EXIT /B 1
:CREATED

:: found a unique directory
SET "UNIQUE=!UNIQUE_DIR!\conda.tmp"
TYPE NUL >!UNIQUE!

:: call conda, exit on error without cleanup
("%CONDA_EXE%" %_CE_M% %_CE_CONDA% shell.cmd.exe %* 1>!UNIQUE!) || EXIT /B 1

:: get temporary script to run
FOR /F %%P IN (!UNIQUE!) DO SET _TEMP_SCRIPT_PATH=%%P
RMDIR /S /Q !UNIQUE_DIR!

:: if no script to run, exit without cleanup
IF NOT DEFINED _TEMP_SCRIPT_PATH EXIT /B 1

:: exit localized variable scope so we can invoke the activation script
ENDLOCAL & SET _TEMP_SCRIPT_PATH=%_TEMP_SCRIPT_PATH%

:: call temporary script
IF DEFINED CONDA_PROMPT_MODIFIER CALL SET "PROMPT=%%PROMPT:%CONDA_PROMPT_MODIFIER%=%%"
(CALL "%_TEMP_SCRIPT_PATH%") || GOTO :ERROR
SET "PROMPT=%CONDA_PROMPT_MODIFIER%%PROMPT%"

:CLEANUP
IF DEFINED CONDA_TEST_SAVE_TEMPS (
    ECHO Retaining activate script "%_TEMP_SCRIPT_PATH%" 1>&2
) ELSE (
    DEL /F /Q "%_TEMP_SCRIPT_PATH%"
)
SET _TEMP_SCRIPT_PATH=
GOTO :EOF

:ERROR
CALL :CLEANUP
EXIT /B 1
