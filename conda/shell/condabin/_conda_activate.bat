:: Copyright (C) 2012 Anaconda, Inc
:: SPDX-License-Identifier: BSD-3-Clause
:: Helper routine for activation, deactivation, and reactivation.
@ECHO OFF

:: Process temporary file from conda - each line is either:
:: 1. A regular environment variable (key=value)
:: 2. An unset operation (key=)
:: 3. A script to run (_CONDA_SCRIPT=script)
FOR /F "usebackq delims=" %%T IN (`"%CONDA_EXE%" %_CE_M% %_CE_CONDA% shell.cmd.exe %*`) DO (
    IF NOT EXIST "%%T" (
        ECHO Failed to run 'conda %*'.
        EXIT /B 2
    ) ELSE (
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
    )
)
@IF %ERRORLEVEL% NEQ 0 (
    ECHO Failed to run 'conda %*'.
    EXIT /B 1
)
