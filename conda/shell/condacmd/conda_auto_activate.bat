@FOR /F "delims=" %%i IN ('%CONDA_EXE% config --show auto_activate_base') DO @SET "__conda_auto_activate_base=%%i"
@IF NOT "x%__conda_auto_activate_base:True=%"=="x%__conda_auto_activate_base%" @CALL %CONDA_BAT% activate base
@SET __conda_auto_activate_base=
