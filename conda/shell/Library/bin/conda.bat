@IF EXIST "%~dp0..\..\Scripts\conda.exe" (
    @SET _CONDA_EXE="%~dp0..\..\Scripts\conda.exe"
) ELSE (
    @SET _CONDA_EXE=python "%~dp0..\..\bin\conda"
)

@IF "%1"=="activate" GOTO :DO_ACTIVATE
@IF "%1"=="deactivate" GOTO :DO_DEACTIVATE

@CALL %_CONDA_EXE% %*

@REM This block should really be the equivalent of
@REM   if "install" in %* GOTO :DO_REACTIVATE
@IF "%1"=="install" GOTO :DO_REACTIVATE
@IF "%1"=="update" GOTO :DO_REACTIVATE
@IF "%1"=="remove" GOTO :DO_REACTIVATE
@IF "%1"=="uninstall" GOTO :DO_REACTIVATE

@GOTO :End


:DO_ACTIVATE
@IF "%CONDA_PS1_BACKUP%"=="" GOTO FIXUP43
    @REM Handle transition from shell activated with conda 4.3 to a subsequent activation
    @REM after conda updated to 4.4. See issue #6173.
    @SET "PROMPT=%CONDA_PS1_BACKUP%"
    @SET CONDA_PS1_BACKUP=
:FIXUP43

@FOR /F "delims=" %%i IN ('@CALL %_CONDA_EXE% shell.cmd.exe activate %*') DO @SET "_TEMP_SCRIPT_PATH=%%i"
@IF "%_TEMP_SCRIPT_PATH%"=="" GOTO :ErrorEnd
@IF "%CONDA_PROMPT_MODIFIER%" == "" GOTO skip_prompt_set_activate
    @CALL SET "PROMPT=%%PROMPT:%CONDA_PROMPT_MODIFIER%=%_empty_not_set_%%%"
:skip_prompt_set_activate
@CALL "%_TEMP_SCRIPT_PATH%"
@DEL /F /Q "%_TEMP_SCRIPT_PATH%"
@SET _TEMP_SCRIPT_PATH=
@SET "PROMPT=%CONDA_PROMPT_MODIFIER%%PROMPT%"

@IF DEFINED PYTHONIOENCODING chcp %PYTHONIOENCODING% > NUL

@GOTO :End

:DO_DEACTIVATE
@FOR /F "delims=" %%i IN ('@CALL %_CONDA_EXE% shell.cmd.exe deactivate %*') DO @SET "_TEMP_SCRIPT_PATH=%%i"
@IF "%_TEMP_SCRIPT_PATH%"=="" GOTO :ErrorEnd
@IF "%CONDA_PROMPT_MODIFIER%" == "" GOTO skip_prompt_set_deactivate
    @CALL SET "PROMPT=%%PROMPT:%CONDA_PROMPT_MODIFIER%=%_empty_not_set_%%%"
:skip_prompt_set_deactivate
@CALL "%_TEMP_SCRIPT_PATH%"
@DEL /F /Q "%_TEMP_SCRIPT_PATH%"
@SET _TEMP_SCRIPT_PATH=
@SET "PROMPT=%CONDA_PROMPT_MODIFIER%%PROMPT%"
@GOTO :End

:DO_REACTIVATE
@FOR /F "delims=" %%i IN ('@CALL %_CONDA_EXE% shell.cmd.exe reactivate') DO @SET "_TEMP_SCRIPT_PATH=%%i"
@IF "%_TEMP_SCRIPT_PATH%"=="" GOTO :ErrorEnd
@CALL "%_TEMP_SCRIPT_PATH%"
@DEL /F /Q "%_TEMP_SCRIPT_PATH%"
@SET _TEMP_SCRIPT_PATH=
@GOTO :End

:End
@SET _CONDA_EXE=
@GOTO :EOF

:ErrorEnd
@SET _CONDA_EXE=
@EXIT /B 1
