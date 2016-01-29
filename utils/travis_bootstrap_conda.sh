#!/bin/sh
# NOTE: this script should be sourced instead of executed


travis_bootstrap_conda() {
    if ! [[ -d $HOME/.conda ]]; then
        declare miniconda_url
        case "$(uname -s | tr '[:upper:]' '[:lower:]')" in
            linux) miniconda_url="https://repo.continuum.io/miniconda/Miniconda-latest-Linux-x86_64.sh";;
            darwin) miniconda_url="https://repo.continuum.io/miniconda/Miniconda-latest-MacOSX-x86_64.sh";;
        esac

        curl -sS -o miniconda.sh "$miniconda_url"
        bash miniconda.sh -bfp $HOME/.conda
        rm -rf miniconda.sh
    fi

    export PATH="$HOME/.conda/bin:$PATH"
    hash -r
    conda config --set always_yes yes
    conda update -q conda

    declare python_version
    case "$TOXENV" in
        py27) python_version="2.7";;
        py33) python_version="3.3";;
        py34) python_version="3.4";;
        py35) python_version="3.5";;
        *)    python_version="3.5";;
    esac
    conda create -q -n test-environment python="$python_version" setuptools pip virtualenv
    source activate test-environment

    if [[ $(uname -s) == "Linux" ]]; then
        export LD_LIBRARY_PATH="$HOME/.conda/envs/test-environment/lib:$LD_LIBRARY_PATH"
    elif [[ $(uname -s) == "Darwin" ]]; then
        export DYLD_LIBRARY_PATH="$HOME/.conda/envs/test-environment/lib:$DYLD_LIBRARY_PATH"
    fi

    conda info -a
    conda list
}

travis_bootstrap_conda
