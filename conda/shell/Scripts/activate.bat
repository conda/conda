:: Copyright (C) 2012 Anaconda, Inc
:: SPDX-License-Identifier: BSD-3-Clause

:: disable displaying the command before execution
@ECHO OFF

:: skip checking for quotes if there are no arguments
IF [%1]==[] GOTO :SKIP_CHECK

:: enter localized variable scope
SETLOCAL

:: Test first character and last character of %1 to see if first character is a "
::   but the last character isn't.
:: This was a bug as described in https://github.com/ContinuumIO/menuinst/issues/60
:: When Anaconda Prompt has the form
::   %windir%\system32\cmd.exe "/K" "C:\Users\builder\Miniconda3\Scripts\activate.bat" "C:\Users\builder\Miniconda3"
:: Rather than the correct
::    %windir%\system32\cmd.exe /K ""C:\Users\builder\Miniconda3\Scripts\activate.bat" "C:\Users\builder\Miniconda3""
:: this solution taken from https://stackoverflow.com/a/31359867

SET "_ARG=%1"
SET _ARG_FIRST=%_ARG:~0,1%
SET _ARG_LAST=%_ARG:~-1%
SET _ARG_FIRST=%_ARG_FIRST:"=+%
SET _ARG_LAST=%_ARG_LAST:"=+%

:: if the first character is not a quote we can skip further quote checking
IF NOT [%_ARG_FIRST%]==[+] ENDLOCAL & GOTO :SKIP_CHECK

:: the first and last characters appear to be matching quotes so we can activate normally
IF [%_ARG_LAST%]==[+] ENDLOCAL & GOTO :SKIP_CHECK

:: found a quote mismatch, we assume this is a bug in the downstream code
ENDLOCAL & CALL "%~dp0\..\condabin\conda.bat" activate
GOTO :EOF

:SKIP_CHECK

:: invoke conda
CALL "%~dp0\..\condabin\conda.bat" activate %*
