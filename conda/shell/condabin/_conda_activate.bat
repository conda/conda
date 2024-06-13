:: Copyright (C) 2012 Anaconda, Inc
:: SPDX-License-Identifier: BSD-3-Clause
:: Helper routine for activation, deactivation, and reactivation.

@IF "%CONDA_PS1_BACKUP%"=="" GOTO :FIXUP43
    :: Handle transition from shell activated with conda 4.3 to a subsequent activation
    :: after conda updated to 4.4. See issue #6173.
    @SET "PROMPT=%CONDA_PS1_BACKUP%"
    @SET CONDA_PS1_BACKUP=
:FIXUP43

:: attempt to find a unique temporary directory to use
@FOR %%A IN ("%TMP%") DO @SET TMP=%%~sA
@SET _I=100
:CREATE
@IF [%_I%]==[0] @(
    @ECHO Failed to create temp directory "%TMP%\conda-<RANDOM>\" 1>&2
    @SET _I=
    @EXIT /B 1
)
@SET /A _I-=1
@SET "_CONDA_TMPDIR=%TMP%\conda-%RANDOM%"
@MKDIR "%_CONDA_TMPDIR%" >NUL 2>NUL || @GOTO :CREATE
@SET _I=

:: found a unique directory
@SET "_CONDA_SCRIPT=%_CONDA_TMPDIR%\conda_activate.bat"
@TYPE NUL >%_CONDA_SCRIPT%

:: call conda
@CALL "%CONDA_EXE%" %_CE_M% %_CE_CONDA% shell.cmd.exe %* >%_CONDA_SCRIPT% || @GOTO :ERROR

:: call temporary script
@IF DEFINED CONDA_PROMPT_MODIFIER @CALL @SET "PROMPT=%%PROMPT:%CONDA_PROMPT_MODIFIER%=%%"
@CALL "%_CONDA_SCRIPT%" || @GOTO :ERROR
@SET "PROMPT=%CONDA_PROMPT_MODIFIER%%PROMPT%"

:CLEANUP
@IF EXIST "%_CONDA_TMPDIR%" @(
    @IF DEFINED CONDA_TEST_SAVE_TEMPS @(
        @IF EXIST "%_CONDA_SCRIPT%" @(
            @ECHO CONDA_TEST_SAVE_TEMPS :: retaining %_CONDA_SCRIPT% 1>&2
        ) ELSE @(
            @ECHO CONDA_TEST_SAVE_TEMPS :: no script to retain 1>&2
            @RMDIR /S /Q %_CONDA_TMPDIR%
        )
    ) ELSE @(
        @RMDIR /S /Q %_CONDA_TMPDIR%
    )
)
@SET _CONDA_SCRIPT=
@SET _CONDA_TMPDIR=
@GOTO :EOF

:ERROR
@CALL :CLEANUP
@EXIT /B 1
