@IF "%CONDA_PS1_BACKUP%"=="" GOTO FIXUP43
    @REM Handle transition from shell activated with conda 4.3 to a subsequent activation
    @REM after conda updated to 4.4. See issue #6173.
    @SET "PROMPT=%CONDA_PS1_BACKUP%"
    @SET CONDA_PS1_BACKUP=
:FIXUP43

@FOR /F "delims=" %%i IN ('@CALL %CONDA_EXE% shell.cmd.exe %*') DO @SET "_TEMP_SCRIPT_PATH=%%i"
@IF "%_TEMP_SCRIPT_PATH%"=="" @EXIT /B 1
@IF "%CONDA_PROMPT_MODIFIER%" == "" GOTO skip_prompt_set_activate
    @CALL SET "PROMPT=%%PROMPT:%CONDA_PROMPT_MODIFIER%=%_empty_not_set_%%%"
:skip_prompt_set_activate
@CALL "%_TEMP_SCRIPT_PATH%"
@DEL /F /Q "%_TEMP_SCRIPT_PATH%"
@SET _TEMP_SCRIPT_PATH=
@SET "PROMPT=%CONDA_PROMPT_MODIFIER%%PROMPT%"

@IF DEFINED PYTHONIOENCODING chcp %PYTHONIOENCODING% > NUL
