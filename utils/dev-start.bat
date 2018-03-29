IF EXIST devenv GOTO :NEXT

powershell.exe -ExecutionPolicy Bypass -NoLogo -NonInteractive -NoProfile -WindowStyle Hidden -Command "(New-Object System.Net.WebClient).DownloadFile('https://repo.continuum.io/miniconda/Miniconda3-latest-Windows-x86_64.exe', 'miniconda.exe')"
start /wait \"\" miniconda.exe /InstallationType=JustMe /RegisterPython=0 /AddToPath=0 /S /D=devenv
devenv\Scripts\conda install -y -c defaults -c conda-forge pytest pytest-cov pytest-timeout mock responses pexpect xonsh


:NEXT
devenv\python -m conda init --dev
CALL dev-init
