@IF NOT DEFINED CONDA_EXE @SET CONDA_EXE="%~dp0..\Scripts\conda.exe"

@IF "%1"=="activate" conda-activate %*
@IF "%1"=="deactivate" conda-activate %*

@CALL %CONDA_EXE% %*
@IF %errorlevel% NEQ 0 exit /b %errorlevel%

@IF "%1"=="install" conda-activate reactivate
@IF "%1"=="update" conda-activate reactivate
@IF "%1"=="remove" conda-activate reactivate
@IF "%1"=="uninstall" conda-activate reactivate
