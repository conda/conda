@IF "%~1"=="" (
    @SET devenv=%CD%\devenv
) ELSE (
    @SET "devenv=%~1"
)
@IF "%~2"=="" (
    @SET pyver=3
) ELSE (
    @SET "pyver=%~2"
)

@REM Unset some variables that get in the way
set CONDA_BAT=
set CONDA_EXE=
set CONDA_SHLVL=
set PYTHONPATH=
set PYTHONHOME=

@IF EXIST "dev-init.bat" @GOTO :INIT_BUILD
@IF EXIST "%devenv%\conda-meta\history" @GOTO :ALREADY
@ECHO Downloading Miniconda%pyver%-latest-Windows-x86_64.exe as miniconda.exe
@powershell.exe -NoProfile -Command (new-object System.Net.WebClient).DownloadFile('https://repo.continuum.io/miniconda/Miniconda%pyver%-latest-Windows-x86_64.exe','miniconda.exe')
@ECHO Installing miniconda to: %devenv%
@start /wait "" miniconda.exe /InstallationType=JustMe /RegisterPython=0 /AddToPath=0 /S /D=%devenv%
call "%devenv%"\Scripts\activate.bat
conda install -y defaults::git
@ECHO exit at this point.

:ALREADY
call "%devenv%"\Scripts\activate.bat

@REM Unset some variables that get in the way
set CONDA_BAT=
set CONDA_EXE=
set CONDA_SHLVL=
set PYTHONPATH=
set PYTHONHOME=

@ECHO               ^>^> conda update -p "%devenv%" -yq --all
@CALL "%devenv%\Scripts\conda" update -p "%devenv%" -yq --all
@ECHO               ^>^> conda install -yp "%devenv%" defaults::git
@CALL "%devenv%\Scripts\conda" install -yp "%devenv%" defaults::git
@ECHO               ^>^> conda install -yq -p "%devenv%" --file dev/test-requirements.txt -c defaults
@CALL "%devenv%\Scripts\conda" install -yq -p "%devenv%" --file dev/test-requirements.txt -c defaults

@CALL "%devenv%\python" -m conda init --dev cmd.exe > NUL

:INIT_BUILD
@CALL dev-init.bat
