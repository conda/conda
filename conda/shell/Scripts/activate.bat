@REM Test first character and last character of %1 to see if first character is a "
@REM   but the last character isn't.
@REM This was a bug as described in https://github.com/ContinuumIO/menuinst/issues/60
@REM When Anaconda Prompt has the form
@REM   %windir%\system32\cmd.exe "/K" "C:\Users\builder\Miniconda3\Scripts\activate.bat" "C:\Users\builder\Miniconda3"
@REM Rather than the correct
@REM    %windir%\system32\cmd.exe /K ""C:\Users\builder\Miniconda3\Scripts\activate.bat" "C:\Users\builder\Miniconda3""
@REM this solution taken from https://stackoverflow.com/a/31359867
@set "_c1=%1"
@set _c1f=%_c1:~0,1%
@set _c1l=%_c1:~-1%
@set _c1f=%_c1f:"=+%
@set _c1l=%_c1l:"=+%
@set _c1=

@if "%_c1f%"=="+" if NOT "%_c1l%"=="+" (
    @CALL "%~dp0..\Library\bin\conda.bat" activate
    @GOTO :End
)

@CALL "%~dp0..\Library\bin\conda.bat" activate %*

:End
@set _c1f=
@set _c1l=
