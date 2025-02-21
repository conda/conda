:: Copyright (C) 2012 Anaconda, Inc
:: SPDX-License-Identifier: BSD-3-Clause
:: Helper routine for activation, deactivation, and reactivation.
@ECHO OFF
SETLOCAL
SET "__conda_tmp=%TEMP%\__conda_tmp_%RANDOM%.txt"

:: Run conda command and get its output
:: WARNING: This cannot be simplified into a FOR /F parsing loop because of the way
:: MSDOS associates the outer quotes for usebackq. E.g., the following:
::   `"%CONDA_EXE%" shell.cmd.exe activate "name"`
:: Which results in the following gibberish being run:
::   %CONDA_EXE%" shell.cmd.exe activate "environment
:: Producing an error like:
::   The filename, directory name, or volume label syntax is incorrect.
:: Instead we run the command and store the output for subsequent processing.
"%CONDA_EXE%" %_CE_M% %_CE_CONDA% shell.cmd.exe %* > "%__conda_tmp%"
IF %ERRORLEVEL% NEQ 0 (
    ECHO Failed to run 'conda %*'.
    IF EXIST "%__conda_tmp%" DEL /F /Q "%__conda_tmp%" 2>NUL
    ENDLOCAL & EXIT /B 1
)

:: Check if conda produced output
FOR /F "delims=" %%T IN (%__conda_tmp%) DO (
    IF NOT EXIST "%%T" (
        ECHO Failed to run 'conda %*'.
        DEL /F /Q "%__conda_tmp%" 2>NUL
        ENDLOCAL & EXIT /B 2
    ) ELSE ENDLOCAL & (
        FOR /F "tokens=1,* delims==" %%A IN (%%T) DO (
            IF "%%A"=="_CONDA_SCRIPT" (
                :: Script execution
                CALL "%%B"
            ) ELSE IF "%%B"=="" (
                :: Unset variable
                SET "%%A="
            ) ELSE (
                :: Set variable
                SET "%%A=%%B"
            )
        )
        :: Clean up
        DEL /F /Q "%%T" 2>NUL
        DEL /F /Q "%__conda_tmp%" 2>NUL
        EXIT /B 0
    )
)

:: If we get here, the FOR loop never ran which means no output
ECHO Failed to run 'conda %*'.
IF EXIST "%__conda_tmp%" DEL /F /Q "%__conda_tmp%" 2>NUL
ENDLOCAL & EXIT /B 3
