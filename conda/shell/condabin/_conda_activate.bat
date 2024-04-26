:: Copyright (C) 2012 Anaconda, Inc
:: SPDX-License-Identifier: BSD-3-Clause
:: Helper routine for activation, deactivation, and reactivation.

@IF DEFINED CONDA_PS1_BACKUP (
    :: Handle transition from shell activated with conda 4.3 to a subsequent activation
    :: after conda updated to 4.4. See issue #6173.
    @SET "PROMPT=%CONDA_PS1_BACKUP%"
    @SET CONDA_PS1_BACKUP=
)

@SETLOCAL EnableDelayedExpansion
@FOR %%A IN ("%TMP%") DO @SET TMP=%%~sA
:: It seems that it is not possible to have "CONDA_EXE=Something With Spaces"
:: and %* to contain: activate "Something With Spaces does not exist".
:: MSDOS associates the outer "'s and is unable to run very much at all.
:: @SET CONDA_EXES="%CONDA_EXE%" %_CE_M% %_CE_CONDA%
:: @FOR /F %%i IN ('%CONDA_EXES% shell.cmd.exe %*') DO @SET _TEMP_SCRIPT_PATH=%%i not return error
:: This method will not work if %TMP% contains any spaces.
@FOR /L %%I IN (1,1,100) DO @(
    @SET UNIQUE_DIR=%TMP%\conda-!RANDOM!
    @MKDIR !UNIQUE_DIR! >NUL 2>NUL
    @IF [%ERRORLEVEL%]==[0] (
        @SET UNIQUE=!UNIQUE_DIR!\conda.tmp
        @TYPE NUL 1> !UNIQUE!
        @GOTO :TMP_FILE_CREATED
    )
)
@ECHO Failed to create temp directory "%TMP%\conda-<RANDOM>\" 1>&2
@EXIT /B 1
:TMP_FILE_CREATED

:: call conda
@"%CONDA_EXE%" %_CE_M% %_CE_CONDA% shell.cmd.exe %* 1>%UNIQUE%
@IF NOT [%ERRORLEVEL%]==[0] @EXIT /B %ERRORLEVEL%

:: get temporary script to run
@FOR /F %%i IN (%UNIQUE%) DO @SET _TEMP_SCRIPT_PATH=%%i
@RMDIR /S /Q %UNIQUE_DIR%
@FOR /F "delims=" %%A IN (""!_TEMP_SCRIPT_PATH!"") DO @ENDLOCAL & @SET _TEMP_SCRIPT_PATH=%%~A
@IF NOT DEFINED _TEMP_SCRIPT_PATH @EXIT /B 1

:: call temporary script
@IF DEFINED CONDA_PROMPT_MODIFIER @CALL SET "PROMPT=%%PROMPT:%CONDA_PROMPT_MODIFIER%=%%"
@CALL "%_TEMP_SCRIPT_PATH%"
@SET "PROMPT=%CONDA_PROMPT_MODIFIER%%PROMPT%"
@IF NOT [%ERRORLEVEL%]==[0] @EXIT /B %ERRORLEVEL%

:: cleanup
@IF DEFINED CONDA_TEST_SAVE_TEMPS @ECHO CONDA_TEST_SAVE_TEMPS :: retaining activate_batch %_TEMP_SCRIPT_PATH% 1>&2
@IF NOT DEFINED CONDA_TEST_SAVE_TEMPS @DEL /F /Q "%_TEMP_SCRIPT_PATH%"
@SET _TEMP_SCRIPT_PATH=
