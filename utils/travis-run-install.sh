set -e
set -x

osx_setup() {
    echo "OSX SETUP ($(pwd))"

    # update Homebrew basics
    brew update || brew update
    brew outdated openssl || brew upgrade openssl

    # test for shells before trying to install them
    [[ $(which -s dash) ]] || brew install dash
    [[ $(which -s zsh) ]] || brew install zsh
    [[ $(which -s tcsh) ]] || brew install tcsh
    # pure csh is not available via brew, but since many users of
    # csh are actually using tcsh whether they know it or not this
    # is a decent substitute
    [[ $(which -s csh) ]] || ln -s "$(which tcsh)" "$(which tcsh | sed 's|tcsh|csh|')"
    # no posh or substitute available via brew

    # install pyenv
    git clone https://github.com/yyuu/pyenv.git ~/.pyenv
    PYENV_ROOT="~/.pyenv"
    PATH="$PYENV_ROOT/bin:$PATH"
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

    export PYTHON_EXE="$(pyenv which python)"

    echo "END OSX SETUP ($(pwd))"
}

linux_setup() {
    echo "LINUX SETUP ($(pwd))"

    export PYTHON_EXE="$(which python)"

    echo "END LINUX SETUP ($(pwd))"
}

python_install() {
    echo "PYTHON INSTALL ($(pwd))"

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

    echo "END PYTHON INSTALL ($(pwd))"
}


flake8_extras() {
    echo "FLAKE8 EXTRAS ($(pwd))"

    # install/update flake8 dependencies
    python -m pip install -U flake8

    echo "END FLAKE8 EXTRAS ($(pwd))"
}


test_extras() {
    echo "TEST EXTRAS ($(pwd))"

    # install/upgrade unittest dependencies
    python -m pip install -U mock pytest pytest-cov pytest-timeout radon \
                             responses anaconda-client nbformat

    echo "END TEST EXTRAS ($(pwd))"
}


miniconda_install() {
    echo "MINICONDA INSTALL ($(pwd))"

    # get, install, and verify miniconda
    curl http://repo.continuum.io/miniconda/Miniconda3-4.0.5-Linux-x86_64.sh -o ~/miniconda.sh
    bash ~/miniconda.sh -bfp ~/miniconda
    export PATH=~/miniconda/bin:$PATH
    hash -r
    which -a conda
    conda info

    # install and verify pip
    conda install -y -q pip
    which -a pip

    # verify python
    which -a python

    # disable automatic updates
    conda config --set auto_update_conda false

    echo "END MINICONDA INSTALL ($(pwd))"
}


conda_build_extras() {
    echo "CONDA BUILD INSTALL ($(pwd))"

    # install conda
    python setup.py install
    conda info

    # install conda-build test dependencies
    conda install -y -q pytest pytest-cov pytest-timeout mock
    python -m pip install pytest-capturelog
    conda install -y -q anaconda-client numpy
    conda install -y -q -c conda-forge perl pytest-xdist
    conda config --set add_pip_as_python_dependency true

    # install conda-build runtime dependencies
    conda install -y -q filelock jinja2 patchelf

    # install conda-build
    git clone -b $CONDA_BUILD --single-branch --depth 1000 https://github.com/conda/conda-build.git
    pushd conda-build
    python setup.py install
    conda info
    popd

    git clone https://github.com/conda/conda_build_test_recipe.git

    echo "END CONDA BUILD INSTALL ($(pwd))"
}


if [[ $FLAKE8 == true ]]; then
    python_install
    flake8_extras
elif [[ -n $CONDA_BUILD ]]; then
    miniconda_install
    conda_build_extras
else
    python_install
    test_extras
fi
