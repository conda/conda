@IF NOT DEFINED CONDA_SHLVL @GOTO :INITIALIZE_SHELL

@CALL "%~dp0..\Library\bin\conda.bat" %*
@GOTO :EOF

:INITIALIZE_SHELL
@FOR %%F in ("%~dp0") do @SET __conda_exe_dir=%%~dpF
@SET "PATH=%__conda_exe_dir%;%PATH%"
@SET CONDA_SHLVL=0
