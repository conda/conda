#!/bin/sh

if ! [ -d devenv ]; then
    if [ `uname` == Darwin ]; then
        curl https://repo.continuum.io/miniconda/Miniconda3-latest-MacOSX-x86_64.sh -o miniconda.sh
        bash miniconda.sh -bfp ./devenv
        ./devenv/bin/conda install -y -c defaults -c conda-forge pytest pytest-cov pytest-timeout mock responses pexpect xonsh
    elif [ `uname` == Linux ]; then
        curl https://repo.continuum.io/miniconda/Miniconda3-latest-Linux-x86_64.sh -o miniconda.sh
        bash miniconda.sh -bfp ./devenv
        ./devenv/bin/conda install -y -c defaults -c conda-forge pytest pytest-cov pytest-timeout mock responses pexpect xonsh
    else
        powershell.exe -ExecutionPolicy Bypass -NoLogo -NonInteractive -NoProfile -WindowStyle Hidden -Command "(New-Object System.Net.WebClient).DownloadFile('https://repo.continuum.io/miniconda/Miniconda3-latest-Windows-x86_64.exe', 'miniconda.exe')"
        cmd.exe /c "start /wait \"\" miniconda.exe /InstallationType=JustMe /RegisterPython=0 /AddToPath=0 /S /D=devenv"
        ./devenv/Scripts/conda install -y -c defaults -c conda-forge pytest pytest-cov pytest-timeout mock responses pexpect xonsh
    fi
fi

eval "$(./devenv/bin/python -m conda init --dev bash)"
