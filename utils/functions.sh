set_vars() {
    # Set global variables
    case "$(uname -s)" in
        'Darwin')
            export ON_WIN=1
            export MINICONDA_URL="https://repo.continuum.io/miniconda/Miniconda3-4.3.11-MacOSX-x86_64.sh"
            export BIN_DIR="bin"
            export EXE_EXT=""
            export INSTALL_PREFIX=~/miniconda
            ;;
        'Linux')
            export ON_WIN=1
            export MINICONDA_URL="https://repo.continuum.io/miniconda/Miniconda3-4.3.11-Linux-x86_64.sh"
            export BIN_DIR="bin"
            export EXE_EXT=""
            export INSTALL_PREFIX=~/miniconda
            ;;
        CYGWIN*|MINGW*|MSYS*)
            export ON_WIN=0
            export MINICONDA_URL="https://repo.continuum.io/miniconda/Miniconda3-4.3.11-Windows-x86_64.exe"
            export BIN_DIR="Scripts"
            export EXE_EXT=".exe"
            export INSTALL_PREFIX=/c/conda-root
            ;;
        *)  ;;
    esac

    if [[ $SUDO == true ]]; then
        export INSTALL_PREFIX=/usr/local
    fi

    if [ $ON_WIN -eq 0 ]; then
        export PYTHON_EXE="$INSTALL_PREFIX/python.exe"
        export CONDA_EXE="$INSTALL_PREFIX/Scripts/conda.exe"
    else
        export PYTHON_EXE="$INSTALL_PREFIX/bin/python"
        export CONDA_EXE="$INSTALL_PREFIX/bin/conda"
    fi

}

set_vars


install_miniconda() {
    local prefix=${1:-$INSTALL_PREFIX}

    if ! [ -f "$prefix/$BIN_DIR/conda$EXE_EXT" ]; then
        if [ $ON_WIN -eq 0 ]; then
            local user_profile="$(cmd.exe /c "echo %USERPROFILE%")"
            if ! [ -f "$user_profile\miniconda.exe" ]; then
                curl -sSL $MINICONDA_URL -o "$user_profile\miniconda.exe"
            fi
            local install_prefix="$(cygpath --windows $prefix)"
            cmd.exe /c "start /wait \"\" %UserProfile%\miniconda.exe /InstallationType=JustMe /RegisterPython=0 /AddToPath=0 /S /D=$install_prefix"
        else
            if ! [ -f ~/miniconda.sh ]; then
                curl -sSL $MINICONDA_URL -o ~/miniconda.sh
            fi
            chmod +x ~/miniconda.sh
            mkdir -p $prefix
            ~/miniconda.sh -bfp $prefix
        fi
    fi
    "$prefix/$BIN_DIR/conda$EXE_EXT" info
}


remove_conda() {
    # requires $PYTHON_EXE

    local prefix=${1:-$INSTALL_PREFIX}
    local site_packages=$($PYTHON_EXE -c "from distutils.sysconfig import get_python_lib as g; print(g())")
    rm -rf \
       $prefix/$BIN_DIR/activate* \
       $prefix/$BIN_DIR/conda* \
       $prefix/$BIN_DIR/deactivate* \
       $prefix/etc/profile.d/conda.sh \
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
    ls -al $site_packages
    hash -r
}


install_python() {
    local prefix=${1:-$INSTALL_PREFIX}
    local python_version=${2:-$PYTHON_VERSION}

    install_miniconda $prefix
    $prefix/$BIN_DIR/conda install -y -q python=$python_version setuptools pip
    remove_conda $prefix

    $PYTHON_EXE --version
    $prefix/$BIN_DIR/pip --version
}


install_conda_shell_scripts() {
    # requires CONDA_EXE be set

    local prefix=${1:-$INSTALL_PREFIX}
    local src_dir=${2:-${SRC_DIR:-$PWD}}

    mkdir -p $prefix/etc/profile.d/
    echo "_CONDA_EXE=\"$CONDA_EXE\"" > $prefix/etc/profile.d/conda.sh
    cat $src_dir/shell/conda.sh >> $prefix/etc/profile.d/conda.sh

    local bin_dir="$prefix/$BIN_DIR"
    mkdir -p $bin_dir
    echo "#!/bin/sh" > $bin_dir/activate
    echo "_CONDA_ROOT=\"$prefix\"" >> $bin_dir/activate
    cat $src_dir/shell/activate >> $bin_dir/activate
    chmod +x $bin_dir/activate  # we really shouldn't be doing this, but needed to make activate_help test pass
    echo "#!/bin/sh" > $bin_dir/activate
    echo "_CONDA_ROOT=\"$prefix\"" >> $bin_dir/deactivate
    cat $src_dir/shell/deactivate >> $bin_dir/deactivate
    chmod +x $bin_dir/deactivate  # we really shouldn't be doing this, but needed to make activate_help test pass

    mkdir -p $prefix/etc/fish/conf.d/
    cp $src_dir/shell/conda.fish $prefix/etc/fish/conf.d/

}


make_conda_entrypoint() {
    local filepath="$1"
    local pythonpath="$2"
    local workingdir="$3"
    local function_import="$4"
    rm -rf $filepath
	cat <<- EOF > $filepath
	#!$pythonpath
	if __name__ == '__main__':
	   import sys
	   sys.path.insert(0, '$workingdir')
	   $function_import
	   sys.exit(main())
	EOF
    chmod +x $filepath
    cat $filepath
}


install_conda_dev() {
    local prefix=${1:-$INSTALL_PREFIX}
    local src_dir=${2:-${SRC_DIR:-$PWD}}

    install_python $prefix

    $prefix/$BIN_DIR/pip install -r utils/requirements-test.txt

    if [ $ON_WIN -eq 0 ]; then
        $PYTHON_EXE utils/setup-testing.py develop  # this, just for the conda.exe and conda-env.exe file
        make_conda_entrypoint "$prefix/Scripts/conda-script.py" "$(cygpath -w "$PYTHON_EXE")" "$(cygpath -w "$src_dir")" "from conda.cli import main"
        make_conda_entrypoint "$prefix/Scripts/conda-env-script.py" "$(cygpath -w "$PYTHON_EXE")" "$(cygpath -w "$src_dir")" "from conda_env.cli.main import main"
    else
        make_conda_entrypoint "$CONDA_EXE" "$PYTHON_EXE" "$src_dir" "from conda.cli import main"
        make_conda_entrypoint "$prefix/bin/conda-env" "$PYTHON_EXE" "$src_dir" "from conda.cli import main"
    fi

    install_conda_shell_scripts "$prefix" "$src_dir"

    mkdir -p $prefix/conda-meta
    touch $prefix/conda-meta/history

    $CONDA_EXE info

    $CONDA_EXE config --set auto_update_conda false
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


set_test_vars() {
    local prefix=${1:-$INSTALL_PREFIX}

    export PYTEST_EXE="$prefix/$BIN_DIR/py.test"
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
    # $PYTEST_EXE $ADD_COV -m "integration and not installed"
}


conda_activate_test() {
    local prefix=${1:-$INSTALL_PREFIX}
#    local prefix=$(python -c "import sys; print(sys.prefix)")
#    ln -sf shell/activate $prefix/bin/activate
#    ln -sf shell/deactivate $prefix/bin/deactivate
#    make_conda_entrypoint $prefix/bin/conda $prefix/bin/python $(pwd)

    if [[ $SUDO == true ]]; then
        sudo $prefix/$BIN_DIR/python -m conda._vendor.auxlib.packaging conda
    else
        $prefix/$BIN_DIR/python -m conda._vendor.auxlib.packaging conda
    fi

    $PYTHON_EXE -c "import conda; print(conda.__version__)"
    $CONDA_EXE info

    # make test-installed
    # $PYTEST_EXE $ADD_COV -m "installed" --shell=bash --shell=zsh
    if [ $ON_WIN -eq 0 ]; then
        $PYTEST_EXE $ADD_COV -m "installed" --shell=cmd.exe --shell=bash.exe
    else
        $PYTEST_EXE $ADD_COV -m "installed" --shell=bash
    fi

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

    # TODO: remove -k flag when conda/conda-build#1927 is merged
    $prefix/bin/python -m pytest --basetemp /tmp/cb -v --durations=20 -n 2 -m "not serial" tests \
        -k "not (pip_in_meta_yaml_fail or disable_pip or xattr or keeps_build_id)"
    $prefix/bin/python -m pytest --basetemp /tmp/cb -v --durations=20 -n 0 -m "serial" tests
    popd
}


osx_setup() {
    # brew update || brew update
    # brew outdated openssl || brew upgrade openssl
    brew install zsh

    # rvm get head

    install_conda_dev
}


usr_local_install() {
    sudo -E bash -c "source utils/functions.sh && install_conda_dev /usr/local"
    sudo chown -R root:root ./conda
    ls -al ./conda
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


windows_setup() {
    install_conda_dev
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
        CYGWIN*|MINGW*|MSYS*)
            windows_setup
            ;;
        *)  ;;
    esac

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
        # conda_build_smoke_test
        conda_build_unit_test
    else
        set_test_vars
        conda_main_test
        conda_activate_test
        $INSTALL_PREFIX/$BIN_DIR/codecov --env PYTHON_VERSION
    fi

    set +e
    set +x
}


