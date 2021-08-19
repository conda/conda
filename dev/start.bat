@IF "%~1"=="" (
    @SET DEVENV=%CD%\devenv
) ELSE (
    @SET "DEVENV=%~1"
)
@IF "%PYTHON%"=="" (
    @SET "PYTHON=3.8"
)

@REM Unset some variables that get in the way
set CONDA_BAT=
set CONDA_EXE=
set CONDA_SHLVL=
set PYTHONPATH=
set PYTHONHOME=

@IF EXIST "dev-init.bat" @GOTO :INIT_BUILD
@IF EXIST "%DEVENV%\conda-meta\history" @GOTO :ALREADY
@ECHO Downloading Miniconda3-latest-Windows-x86_64.exe as miniconda.exe
@powershell.exe -NoProfile -Command (new-object System.Net.WebClient).DownloadFile('https://repo.continuum.io/miniconda/Miniconda3-latest-Windows-x86_64.exe','miniconda.exe')
@ECHO Installing miniconda to: %DEVENV%
@start /wait "" miniconda.exe /InstallationType=JustMe /RegisterPython=0 /AddToPath=0 /S /D=%DEVENV%
call "%DEVENV%"\Scripts\activate.bat
conda install -y defaults::git
@ECHO exit at this point.

:ALREADY
call "%DEVENV%"\Scripts\activate.bat

@REM Unset some variables that get in the way
set CONDA_BAT=
set CONDA_EXE=
set CONDA_SHLVL=
set PYTHONPATH=
set PYTHONHOME=

@ECHO               ^>^> conda update -p "%DEVENV%" -yq --all
@CALL "%DEVENV%\Scripts\conda" update -p "%DEVENV%" -yq --all
@ECHO               ^>^> conda install -yp "%DEVENV%" defaults::git
@CALL "%DEVENV%\Scripts\conda" install -yp "%DEVENV%" defaults::git
@ECHO               ^>^> conda install -yq -p "%DEVENV%" python="%PYTHON%" pywin32 --file tests\requirements.txt -c defaults
@CALL "%DEVENV%\Scripts\conda" install -yq -p "%DEVENV%" python="%PYTHON%" pywin32 --file tests\requirements.txt -c defaults

@CALL "%DEVENV%\python" -m conda init --dev cmd.exe > NUL

:INIT_BUILD
@CALL dev-init.bat
