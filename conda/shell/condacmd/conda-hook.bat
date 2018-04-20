@IF DEFINED CONDA_SHLVL @GOTO :EOF

@FOR %%F in ("%~dp0") do @SET __condacmd_dir=%%~dpF
REM @SET "PATH=%__condacmd_dir%;%PATH%"
@FOR %%F in ("%__condacmd_dir%") do @SET __prefix=%%~dpF
@SET CONDA_EXE="%__prefix%\Scripts\conda.exe"
@DOSKEY conda="%__prefix%\condacmd\conda.bat"
@SET __condacmd_dir=
@SET __prefix=

@SET CONDA_SHLVL=0
@FOR /F "delims=" %%i IN ('@call conda config --show auto_activate_base') DO @SET "__conda_auto_activate_base=%%i"
@IF NOT "x%__conda_auto_activate_base:True=%"=="x%__conda_auto_activate_base%" @CALL conda activate base
@SET __conda_auto_activate_base=
