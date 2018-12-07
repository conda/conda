@IF "%~1"=="" (
    @SET devenv=devenv
) ELSE (
    @SET "devenv=%~1"
)
@IF "%~2"=="" (
    @SET pyver=3
) ELSE (
    @SET "pyver=%~2"
)

@IF EXIST "dev-init.bat" @GOTO :INIT_BUILD
@IF EXIST "%devenv%\conda-meta\history" @GOTO :ALREADY_INSTALLED
@ECHO Downloading Miniconda%pyver%-latest-Windows-x86_64.exe as miniconda.exe
@powershell.exe -NoProfile -Command (new-object System.Net.WebClient).DownloadFile('https://repo.continuum.io/miniconda/Miniconda%pyver%-latest-Windows-x86_64.exe','miniconda.exe')
@ECHO Installing miniconda to: %devenv%
@start /wait "" miniconda.exe /InstallationType=JustMe /RegisterPython=0 /AddToPath=0 /S /D=%CD%\%devenv%
@ECHO ^>^> conda update -yq --all
@CALL "%devenv%\Scripts\conda" update -yq --all
@ECHO ^>^> conda install -yq --file dev/test-requirements.txt -c defaults -c conda-forge
@CALL "%devenv%\Scripts\conda" install -yq --file dev/test-requirements.txt -c defaults -c conda-forge

:ALREADY_INSTALLED
@CALL "%devenv%\python" -m conda init --dev cmd.exe > NUL

:INIT_BUILD
@CALL dev-init.bat
