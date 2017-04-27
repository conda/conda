
@IF NOT "%CONDA_EXE%" == "" GOTO skip_set_conda_exe
@SET "CONDA_EXE=python -m conda"
:skip_set_conda_exe


@IF "%1"=="activate" GOTO :DO_ACTIVATE
@IF "%1"=="deactivate" GOTO :DO_DEACTIVATE

@CALL %CONDA_EXE% %*

@IF "%1"=="install" GOTO :DO_DEACTIVATE
@IF "%1"=="update" GOTO :DO_DEACTIVATE
@IF "%1"=="remove" GOTO :DO_DEACTIVATE
@IF "%1"=="uninstall" GOTO :DO_DEACTIVATE

@GOTO :End


:DO_ACTIVATE
@IF "%CONDA_PROMPT_MODIFIER%" == "" GOTO skip_prompt_set_activate
@CALL SET PROMPT=%%PROMPT:%CONDA_PROMPT_MODIFIER%=%replacement%%%
:skip_prompt_set_activate
@FOR /F "delims=" %%i IN ('@call python -m conda shell.activate cmd.exe %2') DO @SET "TEMP_SCRIPT=%%i"
@CALL "%TEMP_SCRIPT%"
@DEL /F /Q "%TEMP_SCRIPT%"
@SET TEMP_SCRIPT=
@SET "PROMPT=%CONDA_PROMPT_MODIFIER%%PROMPT%"
@GOTO :End

:DO_DEACTIVATE
@IF "%CONDA_PROMPT_MODIFIER%" == "" GOTO skip_prompt_set_deactivate
@CALL SET PROMPT=%%PROMPT:%CONDA_PROMPT_MODIFIER%=%replacement%%%
:skip_prompt_set_deactivate
@FOR /F "delims=" %%i IN ('@call python -m conda shell.deactivate cmd.exe') DO @SET "TEMP_SCRIPT=%%i"
@CALL "%TEMP_SCRIPT%"
@DEL /F /Q "%TEMP_SCRIPT%"
@SET TEMP_SCRIPT=
@SET "PROMPT=%CONDA_PROMPT_MODIFIER%%PROMPT%"
@GOTO :End

:DO_REACTIVATE
@FOR /F "delims=" %%i IN ('@call python -m conda shell.reactivate cmd.exe') DO @SET "TEMP_SCRIPT=%%i"
@CALL "%TEMP_SCRIPT%"
@DEL /F /Q "%TEMP_SCRIPT%"
@SET TEMP_SCRIPT=
@GOTO :End

:End
@SET CONDA_EXE=
@GOTO :eof
