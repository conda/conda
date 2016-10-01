#!/usr/bin/env bash
# NOTE: this script should be sourced instead of executed

# turn ON immediate error termination
set -e
# turn ON verbose printing of commands/results
set -x

# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #
# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #
# #                                                                     # #
# # TRAVIS CI INSTALL                                                   # #
# #                                                                     # #
# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #
# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #

###########################################################################
# HELPER FUNCTIONS                                                        #
osx_setup() {
    echo "OSX SETUP"

    # update Homebrew basics
    brew update || brew update

    # install/update openssl
    if [[ $(brew list | grep openssl) ]]; then
        brew outdated openssl || brew upgrade openssl
    else
        brew install openssl
    fi

    # test for shells before trying to install them
    if [[ $(brew list | grep dash) ]]; then
        brew outdated dash || brew upgrade dash
    else
        brew install dash
    fi
    if [[ $(brew list | grep zsh) ]]; then
        brew outdated zsh || brew upgrade zsh
    else
        brew install zsh
    fi
    if [[ $(brew list | grep ksh) ]]; then
        brew outdated ksh || brew upgrade ksh
    else
        brew install ksh
    fi
    if [[ $(brew list | grep tcsh) ]]; then
        brew outdated tcsh || brew upgrade tcsh
    else
        brew install tcsh
    fi
    # pure csh is not available via brew, but since many users of
    # csh are actually using tcsh whether they know it or not this
    # is a decent substitute
    if [[ $(which csh) ]]; then
        :
    else
        ln -s "$(which tcsh)" "$(which tcsh | sed 's|tcsh|csh|')"
    fi
    # no posh or substitute available via brew

    # install pyenv
    if [[ -d "${HOME}/.pyenv" ]]; then
        :
    else
        git clone "https://github.com/yyuu/pyenv.git" "${HOME}/.pyenv"
    fi
    PYENV_ROOT="${HOME}/.pyenv"
    PATH=$(./shell/envvar_cleanup.bash "$PYENV_ROOT/bin:$PATH" -d)
    export PATH
    eval "$(pyenv init -)"

    # install the specified python version
    case "$PYTHON_VERSION" in
        '2.7')
            curl -O https://bootstrap.pypa.io/get-pip.py
            python get-pip.py --user
            ;;
        '3.4')
            pyenv install 3.4.4
            pyenv global 3.4.4
            ;;
        '3.5')
            pyenv install 3.5.1
            pyenv global 3.5.1
            ;;
    esac
    pyenv rehash

    PYTHON_EXE="$(pyenv which python)"
    export PYTHON_EXE

    echo "END OSX SETUP"
}


linux_setup() {
    echo "LINUX SETUP"

    PYTHON_EXE="$(which python)"
    export PYTHON_EXE

    echo "END LINUX SETUP"
}


python_install() {
    echo "PYTHON INSTALL"

    case "$(uname -s)" in
        'Darwin')
            osx_setup
            ;;
        'Linux')
            linux_setup
            ;;
        *)  ;;
    esac

    # install/upgrade basic dependencies
    python -m pip install -U psutil ruamel.yaml pycosat pycrypto
    case "${TRAVIS_PYTHON_VERSION:-PYTHON_VERSION}" in
        '2.7')
            python -m pip install -U enum34 futures;;
        *)  ;;
    esac

    echo "END PYTHON INSTALL"
}


flake8_extras() {
    echo "FLAKE8 EXTRAS"

    # install/update flake8 dependencies
    python -m pip install -U flake8

    echo "END FLAKE8 EXTRAS"
}


test_extras() {
    echo "TEST EXTRAS"

    # install/upgrade unittest dependencies
    python -m pip install -U mock pytest pytest-cov pytest-timeout radon \
                             responses anaconda-client nbformat

    echo "END TEST EXTRAS"
}


miniconda_install() {
    echo "MINICONDA INSTALL"

    [[ -f "${HOME}/.condarc" ]] && rm -f "${HOME}/.condarc"

    # get, install, and verify miniconda
    if [[ ! -d "${HOME}/miniconda" ]]; then
        if [[ ! -f "${HOME}/miniconda.sh" ]]; then
            case "$(uname -s)" in
                'Darwin')
                    MINICONDA_URL="Miniconda3-4.0.5-MacOSX-x86_64.sh"
                    ;;
                'Linux')
                    MINICONDA_URL="Miniconda3-4.0.5-Linux-x86_64.sh"
                    ;;
                *)  ;;
            esac
            curl "http://repo.continuum.io/miniconda/${MINICONDA_URL}" -o "${HOME}/miniconda.sh"
        fi

        bash "${HOME}/miniconda.sh" -bfp "${HOME}/miniconda"
    fi
    PATH="${HOME}/miniconda/bin:${PATH}"
    export PATH
    hash -r
    which -a conda
    # this causes issues with Miniconda3 4.0.5
    # python -m conda info
    # this does not cause issues with Miniconda3 4.0.5
    conda info

    # install and verify pip
    conda install -y -q pip
    which -a pip

    # verify python
    which -a python

    # disable automatic updates
    conda config --set auto_update_conda false

    echo "END MINICONDA INSTALL"
}


conda_build_extras() {
    echo "CONDA BUILD EXTRAS"

    # install conda (the repo exists at $PWD)
    python setup.py install
    conda info

    # install conda-build test dependencies
    conda install -y -q pytest pytest-cov pytest-timeout mock
    python -m pip install pytest-capturelog
    conda install -y -q anaconda-client numpy
    conda install -y -q -c conda-forge perl pytest-xdist
    conda config --set add_pip_as_python_dependency true

    # install conda-build runtime dependencies
    case "$(uname -s)" in
        'Darwin')
            conda install -y -q filelock jinja2
            ;;
        'Linux')
            conda install -y -q filelock jinja2 patchelf
            ;;
        *)  ;;
    esac

    # install conda-build
    if [[ ! -d ./conda-build ]]; then
        git clone -b "${CONDA_BUILD}" --single-branch --depth 1000 https://github.com/conda/conda-build.git
    fi
    pushd conda-build
    python setup.py install
    conda info
    popd

    # get conda-build test recipe
    if [[ ! -d ./conda_build_test_recipe ]]; then
        git clone https://github.com/conda/conda_build_test_recipe.git
    fi

    echo "END CONDA BUILD EXTRAS"
}
# END HELPER FUNCTIONS                                                    #
###########################################################################

###########################################################################
# "MAIN FUNCTION"                                                         #
echo "START INSTALLING"

# show basic environment details                                          #
which -a python
env | sort

# remove duplicates from the $PATH                                        #
# CSH has issues when variables get too long                              #
# a common error that may occur would be a "Word too long" error and is   #
# probably related to the PATH variable, here we use envvar_cleanup.bash  #
# to remove duplicates from the path variable before trying to run the    #
# tests                                                                   #
PATH=$(./shell/envvar_cleanup.bash "$PATH" -d)
export PATH

# perform the appropriate test setup                                      #
if [[ "${FLAKE8}" == true ]]; then
    python_install
    flake8_extras
elif [[ -n "${CONDA_BUILD}" ]]; then
    # running anything with python -m conda in Miniconda3 4.0.5 causes
    # issues, use conda directly
    miniconda_install
    conda_build_extras
else
    python_install
    test_extras
fi

echo "DONE INSTALLING"
# END "MAIN FUNCTION"                                                     #
###########################################################################
