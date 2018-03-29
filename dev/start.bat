@IF EXIST devenv @GOTO :ALREADY_INSTALLED
@powershell.exe -Command (new-object System.Net.WebClient).DownloadFile('https://repo.continuum.io/miniconda/Miniconda3-latest-Windows-x86_64.exe','miniconda.exe')
@start /wait "" miniconda.exe /InstallationType=JustMe /RegisterPython=0 /AddToPath=0 /S /D=%CD%\devenv
@devenv\Scripts\conda conda update -yq --all
@devenv\Scripts\conda install -yq --file dev/test-requirements.txt -c defaults -c conda-forge

:ALREADY_INSTALLED
@devenv\python -m conda init --dev > NUL
@CALL dev-init
