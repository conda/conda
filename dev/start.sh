#!/bin/sh
# NOTE: This script should be sourced! The shebang is only here to help syntax highlighters.

# # conda-build
# pip install --no-deps -U .

if ! [ -d devenv ]; then
    if [ `uname` == Darwin ]; then
        curl https://repo.continuum.io/miniconda/Miniconda3-latest-MacOSX-x86_64.sh -o miniconda.sh
        bash miniconda.sh -bfp ./devenv
        ./devenv/bin/conda update -yq --all
        ./devenv/bin/conda install -yq --file dev/test-requirements.txt -c defaults -c conda-forge
        eval "$(./devenv/bin/python -m conda init --dev bash)"
    elif [ `uname` == Linux ]; then
        curl https://repo.continuum.io/miniconda/Miniconda3-latest-Linux-x86_64.sh -o miniconda.sh
        bash miniconda.sh -bfp ./devenv
        ./devenv/bin/conda update -yq --all
        ./devenv/bin/conda install -yq --file dev/test-requirements.txt -c defaults -c conda-forge
        ./devenv/bin/conda install -yq patchelf  # for conda-build
        eval "$(./devenv/bin/python -m conda init --dev bash)"
    else
        powershell.exe -Command "(new-object System.Net.WebClient).DownloadFile('https://repo.continuum.io/miniconda/Miniconda3-latest-Windows-x86_64.exe','miniconda.exe')"
        cmd.exe /c "start /wait \"\" miniconda.exe /InstallationType=JustMe /RegisterPython=0 /AddToPath=0 /S /D=%CD%\devenv"
        ./devenv/Scripts/conda update -yq --all
        ./devenv/Scripts/conda install -yq --file dev/test-requirements.txt -c defaults -c conda-forge
        eval "$(./python -m conda init --dev bash)"
    fi
fi
