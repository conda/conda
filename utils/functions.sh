# Set global variables
case "$(uname -s)" in
    'Darwin')
        export MINICONDA_URL="https://repo.continuum.io/miniconda/Miniconda3-4.2.12-MacOSX-x86_64.sh"
        ;;
    'Linux')
        export MINICONDA_URL="https://repo.continuum.io/miniconda/Miniconda3-4.2.12-Linux-x86_64.sh"
        ;;
    *)  ;;
esac
export INSTALL_PREFIX=~/miniconda


install_miniconda() {
    local prefix=${1:-$INSTALL_PREFIX}
    curl -sSL $MINICONDA_URL -o ~/miniconda.sh
    chmod +x ~/miniconda.sh
    mkdir -p $prefix
    ~/miniconda.sh -bfp $prefix
}


remove_conda() {
    local prefix=${1:-$INSTALL_PREFIX}
    local site_packages=$($prefix/bin/python -c "from distutils.sysconfig import get_python_lib as g; print(g())")
    rm -rf $prefix/bin/activate \
       $prefix/bin/conda \
       $prefix/bin/conda-env \
       $prefix/bin/deactivate \
       $prefix/conda-meta/conda-*.json \
       $prefix/conda-meta/requests-*.json \
       $prefix/conda-meta/pyopenssl-*.json \
       $prefix/conda-meta/cryptography-*.json \
       $prefix/conda-meta/idna-*.json \
       $prefix/conda-meta/ruamel-*.json \
       $prefix/conda-meta/pycrypto-*.json \
       $prefix/conda-meta/pycosat-*.json \
       $site_packages/conda* \
       $site_packages/requests* \
       $site_packages/pyopenssl* \
       $site_packages/cryptography* \
       $site_packages/idna* \
       $site_packages/ruamel* \
       $site_packages/pycrypto* \
       $site_packages/pycosat*
    hash -r
}


install_python() {
    local prefix=${1:-$INSTALL_PREFIX}
    local python_version=${2:-$PYTHON_VERSION}

    install_miniconda $prefix
    $prefix/bin/conda install -y -q python=$python_version setuptools pip
    remove_conda $prefix

    which python
    $prefix/bin/python --version
    $prefix/bin/pip --version
}


install_conda_dev() {
    local prefix=${1:-$INSTALL_PREFIX}
    install_python $prefix

    $prefix/bin/pip install -r utils/requirements-test.txt
    $prefix/bin/python utils/setup-testing.py develop
    mkdir -p $prefix/conda-meta
    touch $prefix/conda-meta/history

    $prefix/bin/conda info

    $prefix/bin/conda config --set auto_update_conda false
}


install_conda_build() {
    local prefix=${1:-$INSTALL_PREFIX}

    install_conda_dev $prefix

    # install conda-build dependencies (runtime and test)
    $prefix/bin/conda install -y -q -c conda-forge perl pytest-xdist
    $prefix/bin/conda install -y -q \
        anaconda-client numpy \
        filelock jinja2 patchelf conda-verify contextlib2 pkginfo
    $prefix/bin/pip install pytest-catchlog pytest-mock

    $prefix/bin/conda config --set add_pip_as_python_dependency true

    # install conda-build
    git clone -b $CONDA_BUILD --single-branch --depth 100 https://github.com/conda/conda-build.git
    local site_packages=$($prefix/bin/python -c "from distutils.sysconfig import get_python_lib as g; print(g())")
    rm -rf $site_packages/conda_build
    pushd conda-build
    $prefix/bin/pip install .
    popd

    git clone https://github.com/conda/conda_build_test_recipe.git

    $prefix/bin/conda info
}


usr_local_install() {
    export INSTALL_PREFIX="/usr/local"
    sudo -E bash -c "source utils/functions.sh && install_conda_dev /usr/local"
    sudo chown -R root:root ./conda
    ls -al ./conda
}


set_test_vars() {
    local prefix=${1:-$INSTALL_PREFIX}

    export PYTEST_EXE="$prefix/bin/py.test"
    export PYTHON_EXE=$(sed 's/^\#!//' $PYTEST_EXE | head -1)
    export PYTHON_MAJOR_VERSION=$($PYTHON_EXE -c "import sys; print(sys.version_info[0])")
    export TEST_PLATFORM=$($PYTHON_EXE -c "import sys; print('win' if sys.platform.startswith('win') else 'unix')")
    export PYTHONHASHSEED=$($PYTHON_EXE -c "import random as r; print(r.randint(0,4294967296))")

    export ADD_COV="--cov-report xml --cov-report term-missing --cov-append --cov conda"
}


conda_main_test() {
    # make conda-version
    $PYTHON_EXE utils/setup-testing.py --version

    # make integration
    $PYTEST_EXE $ADD_COV -m "not integration and not installed"
    $PYTEST_EXE $ADD_COV -m "integration and not installed"
}



make_conda_entrypoint() {
    local filepath="$1"
    local pythonpath="$2"
    local workingdir="$3"
    ls -al $filepath
    rm -rf $filepath
	cat <<- EOF > $filepath
	#!$pythonpath
	if __name__ == '__main__':
	   import sys
	   sys.path.insert(0, '$workingdir')
	   import conda.cli.main
	   sys.exit(conda.cli.main.main())
	EOF
    chmod +x $filepath
    cat $filepath
}




conda_activate_test() {
    local prefix=${1:-$INSTALL_PREFIX}
#    local prefix=$(python -c "import sys; print(sys.prefix)")
#    ln -sf shell/activate $prefix/bin/activate
#    ln -sf shell/deactivate $prefix/bin/deactivate
#    make_conda_entrypoint $prefix/bin/conda $prefix/bin/python $(pwd)

    if [[ $SUDO == true ]]; then
        sudo $prefix/bin/python utils/setup-testing.py develop
    else
        $prefix/bin/python utils/setup-testing.py develop
    fi

    $prefix/bin/python -c "import conda; print(conda.__version__)"
    $prefix/bin/python -m conda info

    # make test-installed
    # $PYTEST_EXE $ADD_COV -m "installed" --shell=bash --shell=zsh
    $PYTEST_EXE $ADD_COV -m "installed" --shell=bash

}



conda_build_smoke_test() {
    local prefix=${1:-$INSTALL_PREFIX}

    $prefix/bin/conda config --add channels conda-canary
    $prefix/bin/conda build conda.recipe
}


conda_build_unit_test() {
    local prefix=${1:-$INSTALL_PREFIX}

    pushd conda-build
    echo
    echo ">>>>>>>>>>>> running conda-build unit tests >>>>>>>>>>>>>>>>>>>>>"
    echo

    export PATH="$prefix/bin:$PATH"  # cheating
    conda info

    $prefix/bin/python -m pytest --basetemp /tmp/cb -v --durations=20 -n 0 -m "serial" tests
    $prefix/bin/python -m pytest --basetemp /tmp/cb -v --durations=20 -n 2 -m "not serial" tests
    popd
}


osx_setup() {
    # brew update || brew update
    # brew outdated openssl || brew upgrade openssl
    brew install zsh

    # rvm get head

    install_conda_dev
}


linux_setup() {
    if [[ $FLAKE8 == true ]]; then
        pip install flake8
    elif [[ $SUDO == true ]]; then
        usr_local_install
    elif [[ -n $CONDA_BUILD ]]; then
        install_conda_build
    else
        install_conda_dev
    fi
}


run_setup() {
    set -e
    set -x
    env | sort

    case "$(uname -s)" in
        'Darwin')
            osx_setup
            ;;
        'Linux')
            linux_setup
            ;;
        *)  ;;
    esac

    export PATH="$INSTALL_PREFIX:$PATH"

    set +e
    set +x
}


run_tests() {
    set -e
    set -x
    env | sort


    if [[ $FLAKE8 == true ]]; then
        flake8 --statistics
    elif [[ -n $CONDA_BUILD ]]; then
        set_test_vars
        conda_build_smoke_test
        conda_build_unit_test
    else
        set_test_vars
        conda_main_test
        if [[ "$(uname -s)" == "Linux" ]]; then
            conda_activate_test
        fi
        $INSTALL_PREFIX/bin/codecov --env PYTHON_VERSION
    fi

    set +e
    set +x
}


