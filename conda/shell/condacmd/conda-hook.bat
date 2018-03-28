@IF DEFINED CONDA_SHLVL @GOTO :EOF

@FOR %%F in ("%~dp0") do @SET __conda_exe_dir=%%~dpF
@SET "PATH=%__conda_exe_dir%;%PATH%"
@SET __conda_exe_dir=
@SET CONDA_SHLVL=0
@FOR /F "delims=" %%i IN ('@call conda config --show auto_activate_base') DO @SET "__conda_auto_activate_base=%%i"
@IF NOT "x%__conda_auto_activate_base:True=%"=="x%__conda_auto_activate_base%" @CALL conda activate base
@SET __conda_auto_activate_base=
