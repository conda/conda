#!/bin/bash
# NOTE: this script should be sourced instead of executed


travis_bootstrap_conda() {
    local py_major=${PY_VERSION:0:1}

    if ! [[ -d $HOME/miniconda ]]; then
        declare miniconda_url
        case "$(uname -s | tr '[:upper:]' '[:lower:]')" in
            linux) miniconda_url="https://repo.continuum.io/miniconda/Miniconda${py_major}-latest-Linux-x86_64.sh";;
            darwin) miniconda_url="https://repo.continuum.io/miniconda/Miniconda${py_major}-latest-MacOSX-x86_64.sh";;
        esac

        curl -sS -o miniconda.sh "$miniconda_url"
        bash miniconda.sh -bfp $HOME/miniconda
        rm -rf miniconda.sh
    fi

    export PATH="$HOME/miniconda/bin:$PATH"
    hash -r
    conda config --set always_yes yes
    conda update conda

    # TODO: on hold until we get virtualenvs working
    # declare python_version
    # case "$TOXENV" in
    #     py27) python_version="2.7";;
    #     py33) python_version="3.3";;
    #     py34) python_version="3.4";;
    #     py35) python_version="3.5";;
    #     *)    python_version="3.5";;
    # esac

    # conda create -q -n test-environment python="$python_version" setuptools pip virtualenv
    # source activate test-environment

    conda info --all
    conda list
}

travis_bootstrap_conda
