@IF DEFINED CONDA_SHLVL @GOTO :EOF

@FOR %%F in ("%~dp0") do @SET __condacmd_dir=%%~dpF
@SET CONDA_EXE="%__condacmd_dir%..\Scripts\conda.exe"
@SET CONDA_BAT="%__condacmd_dir%conda.bat"
@DOSKEY conda="%__condacmd_dir%conda.bat" $*
@SET __condacmd_dir=

@SET CONDA_SHLVL=0
@FOR /F "delims=" %%i IN ('%CONDA_EXE% config --show auto_activate_base') DO @SET "__conda_auto_activate_base=%%i"
@IF NOT "x%__conda_auto_activate_base:True=%"=="x%__conda_auto_activate_base%" @CALL %CONDA_BAT% activate base
@SET __conda_auto_activate_base=
