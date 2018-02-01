:: Test first character and last character of %1 to see if first character is a "
::   but the last character isn't.
:: This was a bug as described in https://github.com/ContinuumIO/menuinst/issues/60
:: When Anaconda Prompt has the form
::   %windir%\system32\cmd.exe "/K" "C:\Users\builder\Miniconda3\Scripts\activate.bat" "C:\Users\builder\Miniconda3"
:: Rather than the correct
::    %windir%\system32\cmd.exe /K ""C:\Users\builder\Miniconda3\Scripts\activate.bat" "C:\Users\builder\Miniconda3""
@set "_c1=%1"
@set _c1f=%_c1:~0,1%
@set _c1l=%_c1:~-1%
@set _c1f=%_c1f:"=+%
@set _c1l=%_c1l:"=+%

@if "%_c1f%"=="+" if NOT "%_c1l%"=="+" (
    @CALL "%~dp0..\Library\bin\conda.bat" activate
    @GOTO :End
)

@CALL "%~dp0..\Library\bin\conda.bat" activate %*

:End
@set _c1=
@set _c1f=
@set _c1l=
