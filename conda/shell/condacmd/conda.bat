@IF NOT DEFINED CONDA_EXE @SET CONDA_EXE="%~dp0..\Scripts\conda.exe"

@IF "%1"=="activate" conda_activate %*
@IF "%1"=="deactivate" conda_activate %*

@CALL %CONDA_EXE% %*
@IF %errorlevel% NEQ 0 exit /b %errorlevel%

@IF "%1"=="install" conda_activate reactivate
@IF "%1"=="update" conda_activate reactivate
@IF "%1"=="remove" conda_activate reactivate
@IF "%1"=="uninstall" conda_activate reactivate
