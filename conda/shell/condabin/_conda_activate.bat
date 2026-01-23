:: Copyright (C) 2012 Anaconda, Inc
:: SPDX-License-Identifier: BSD-3-Clause
:: Helper routine for activation, deactivation, and reactivation.
@ECHO OFF
SETLOCAL

:: Generate a unique temporary filename using a GUID to support parallel workflows
:: (e.g., `start /b conda run ...`). %RANDOM% is insufficient because processes
:: started simultaneously get identical time-based seeds, producing collisions.
:: See: https://devblogs.microsoft.com/oldnewthing/20100617-00/?p=13673
FOR /F "delims=" %%G IN ('powershell -NoProfile -Command "[guid]::NewGuid()"') DO SET "__conda_guid=%%G"
SET "__conda_tmp=%TEMP%\__conda_tmp_%__conda_guid%.txt"

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
IF NOT EXIST "%__conda_tmp%" (
    ECHO ERROR: Failed to create temp file for 'conda %*'.>&2
    ECHO.>&2
    ECHO This is likely a TEMP directory issue>&2
    ECHO ^(permissions, disk space, or invalid path^).>&2
    ECHO.>&2
    ECHO Ensure TEMP or TMP environment variables point to a writable location.>&2
    ECHO See: https://docs.conda.io/projects/conda/en/stable/user-guide/troubleshooting.html#temp-file-errors>&2
    ENDLOCAL & EXIT /B 1
) ELSE IF %ERRORLEVEL% NEQ 0 (
    ECHO ERROR: 'conda %*' exited with code %ERRORLEVEL%.>&2
    DEL /F /Q "%__conda_tmp%" 2>NUL
    ENDLOCAL & EXIT /B 2
)

:: Check if conda produced output
FOR /F "delims=" %%T IN (%__conda_tmp%) DO (
    IF NOT EXIST "%%T" (
        ECHO ERROR: Activation file missing for 'conda %*'.>&2
        DEL /F /Q "%__conda_tmp%" 2>NUL
        ENDLOCAL & EXIT /B 3
    ) ELSE ENDLOCAL & (
        FOR /F "tokens=1,* delims==" %%A IN (%%T) DO (
            IF "%%A"=="_CONDA_SCRIPT" (
                :: Script execution, fast exit if activation scripts fail
                CALL "%%B" || (
                    ECHO ERROR: Activation script '%%B' failed with code %ERRORLEVEL%.>&2
                    DEL /F /Q "%%T" 2>NUL
                    DEL /F /Q "%__conda_tmp%" 2>NUL
                    EXIT /B 4
                )
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
ECHO ERROR: No output from 'conda %*'.>&2
IF EXIST "%__conda_tmp%" DEL /F /Q "%__conda_tmp%" 2>NUL
ENDLOCAL & EXIT /B 5
