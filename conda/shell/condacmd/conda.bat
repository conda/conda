@IF NOT DEFINED CONDA_EXE @SET CONDA_EXE="%~dp0..\Scripts\conda.exe"

@IF "%1"=="activate" _conda-activate %*
@IF "%1"=="deactivate" _conda-activate %*

@CALL %CONDA_EXE% %*
@IF %errorlevel% NEQ 0 exit /b %errorlevel%

@IF "%1"=="install" _conda-activate reactivate
@IF "%1"=="update" _conda-activate reactivate
@IF "%1"=="remove" _conda-activate reactivate
@IF "%1"=="uninstall" _conda-activate reactivate
