@REM @ symbols in this file indicate that output should not be printed.
@REM   Setting it this way allows us to not touch the user's echo setting.
@REM   For debugging, remove the @ on the section you need to study.


@SET "_CONDA_BAT=%~dp0..\Library\bin\conda.bat"

@CALL %_CONDA_BAT% deactivate "%_CONDA_NEW_ENV%"

@SET _CONDA_BAT=
