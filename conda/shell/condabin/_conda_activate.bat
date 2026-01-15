:: Copyright (C) 2012 Anaconda, Inc
:: SPDX-License-Identifier: BSD-3-Clause
:: Helper routine for activation, deactivation, and reactivation.
@ECHO OFF
SETLOCAL EnableDelayedExpansion

:: Find a writable temp directory with fallback chain
:: Priority: %TEMP% -> %LOCALAPPDATA%\Temp -> %USERPROFILE%\AppData\Local\Temp
SET "__conda_temp_base="

:: Try %TEMP% first (most common)
IF DEFINED TEMP (
    SET "__test_dir=%TEMP%\__conda_writable_test_%RANDOM%"
    MKDIR "!__test_dir!" 2>NUL && (
        RMDIR "!__test_dir!" 2>NUL
        SET "__conda_temp_base=%TEMP%"
    )
)

:: Fallback to %LOCALAPPDATA%\Temp
IF NOT DEFINED __conda_temp_base (
    IF DEFINED LOCALAPPDATA (
        IF EXIST "%LOCALAPPDATA%\Temp" (
            SET "__test_dir=%LOCALAPPDATA%\Temp\__conda_writable_test_%RANDOM%"
            MKDIR "!__test_dir!" 2>NUL && (
                RMDIR "!__test_dir!" 2>NUL
                SET "__conda_temp_base=%LOCALAPPDATA%\Temp"
            )
        )
    )
)

:: Fallback to explicit %USERPROFILE%\AppData\Local\Temp
IF NOT DEFINED __conda_temp_base (
    IF DEFINED USERPROFILE (
        IF EXIST "%USERPROFILE%\AppData\Local\Temp" (
            SET "__test_dir=%USERPROFILE%\AppData\Local\Temp\__conda_writable_test_%RANDOM%"
            MKDIR "!__test_dir!" 2>NUL && (
                RMDIR "!__test_dir!" 2>NUL
                SET "__conda_temp_base=%USERPROFILE%\AppData\Local\Temp"
            )
        )
    )
)

:: If no writable temp found, fail with clear error
IF NOT DEFINED __conda_temp_base (
    ECHO ERROR: Cannot find a writable temporary directory.>&2
    ECHO Tried: %%TEMP%%, %%LOCALAPPDATA%%\Temp, %%USERPROFILE%%\AppData\Local\Temp>&2
    ENDLOCAL & EXIT /B 4
)

:: Create unique temp directory using atomic mkdir (handles parallel activation)
SET "__conda_tmpdir="
FOR /L %%i IN (1,1,100) DO (
    IF NOT DEFINED __conda_tmpdir (
        SET "__try_dir=!__conda_temp_base!\__conda_!RANDOM!!RANDOM!"
        MKDIR "!__try_dir!" 2>NUL && SET "__conda_tmpdir=!__try_dir!"
    )
)

IF NOT DEFINED __conda_tmpdir (
    ECHO ERROR: Failed to create temporary directory after 100 attempts.>&2
    ENDLOCAL & EXIT /B 5
)

SET "__conda_tmp=!__conda_tmpdir!\activate.txt"

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
    IF EXIST "%__conda_tmpdir%" RMDIR /S /Q "%__conda_tmpdir%" 2>NUL
    ENDLOCAL & EXIT /B 1
)

:: Check if conda produced output
FOR /F "delims=" %%T IN (%__conda_tmp%) DO (
    IF NOT EXIST "%%T" (
        ECHO Failed to run 'conda %*'.
        RMDIR /S /Q "%__conda_tmpdir%" 2>NUL
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
        RMDIR /S /Q "%__conda_tmpdir%" 2>NUL
        EXIT /B 0
    )
)

:: If we get here, the FOR loop never ran which means no output
ECHO Failed to run 'conda %*'.
IF EXIST "%__conda_tmpdir%" RMDIR /S /Q "%__conda_tmpdir%" 2>NUL
ENDLOCAL & EXIT /B 3
