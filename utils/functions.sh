set_vars() {
    # Set global variables
    local arch
    case "$PYTHON_ARCH" in 32) arch=x86;; *) arch=x86_64;; esac
    case "$(uname -s)" in
        'Darwin')
            export MINICONDA_URL="https://repo.continuum.io/miniconda/Miniconda3-4.3.11-MacOSX-$arch.sh"
            export BIN_DIR="bin"
            export EXE_EXT=""
            export INSTALL_PREFIX=~/miniconda
            ;;
        'Linux')
            export MINICONDA_URL="https://repo.continuum.io/miniconda/Miniconda3-4.3.11-Linux-$arch.sh"
            export BIN_DIR="bin"
            export EXE_EXT=""
            export INSTALL_PREFIX=~/miniconda
            ;;
        CYGWIN*|MINGW*|MSYS*)
            export ON_WIN=true
            export MINICONDA_URL="https://repo.continuum.io/miniconda/Miniconda3-4.3.11-Windows-$arch.exe"
            export BIN_DIR="Scripts"
            export EXE_EXT=".exe"
            export INSTALL_PREFIX=/c/conda-root
            ;;
        *)  ;;
    esac

    if [ "$SUDO" = true ]; then
        export INSTALL_PREFIX=/usr/local
    fi

    if [ -n "$ON_WIN" ]; then
        export PYTHON_EXE="$INSTALL_PREFIX/python.exe"
        export CONDA_EXE="$INSTALL_PREFIX/Scripts/conda.exe"
    else
        export PYTHON_EXE="$INSTALL_PREFIX/bin/python"
        export CONDA_EXE="$INSTALL_PREFIX/bin/conda"
    fi

    if [ -z "$PYTHON_VERSION" ]; then
        echo "PYTHON_VERSION not set. Defaulting to PYTHON_VERSION=3.6"
        export PYTHON_VERSION=3.6
    fi

}


install_miniconda() {
    local prefix=${1:-$INSTALL_PREFIX}

    if ! [ -f "$prefix/$BIN_DIR/conda$EXE_EXT" ]; then
        if [ -n "$ON_WIN" ]; then
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
    # requires BIN_DIR

    local prefix=${1:-$INSTALL_PREFIX}
    local src_dir=${2:-${SRC_DIR:-$PWD}}
    local symlink_scripts=${3:-1}

    local conda_exe="$prefix/$BIN_DIR/conda$EXE_EXT"

    mkdir -p "$prefix/etc/profile.d/"
    rm -f "$prefix/etc/profile.d/conda.sh"
    echo "_CONDA_ROOT=\"$prefix\"" > "$prefix/etc/profile.d/conda.sh"
    cat "$src_dir/shell/etc/profile.d/conda.sh" >> "$prefix/etc/profile.d/conda.sh"

    mkdir -p "$prefix/$BIN_DIR"

    rm -f "$prefix/$BIN_DIR/activate"
    echo "#!/bin/sh" > "$prefix/$BIN_DIR/activate"
    echo "_CONDA_ROOT=\"$prefix\"" >> "$prefix/$BIN_DIR/activate"
    cat "$src_dir/shell/bin/activate" >> "$prefix/$BIN_DIR/activate"
    chmod +x "$prefix/$BIN_DIR/activate"

    rm -f "$prefix/$BIN_DIR/deactivate"
    echo "#!/bin/sh" > "$prefix/$BIN_DIR/deactivate"
    echo "_CONDA_ROOT=\"$prefix\"" >> "$prefix/$BIN_DIR/deactivate"
    cat "$src_dir/shell/bin/deactivate" >> "$prefix/$BIN_DIR/deactivate"
    chmod +x "$prefix/$BIN_DIR/deactivate"

    if [ -n "$ON_WIN" ]; then
        rm -f "$prefix/$BIN_DIR/activate.bat"
        cp "$src_dir/shell/Scripts/activate.bat" "$prefix/$BIN_DIR/activate.bat"

        rm -f $bin_dir/deactivate.bat
        cp "$src_dir/shell/Scripts/deactivate.bat" "$prefix/$BIN_DIR/deactivate.bat"

        mkdir -p "$prefix/Library/bin"
        rm -f "$prefix/Library/bin/conda.bat"
        local win_conda_exe="$(cygpath --windows "$conda_exe")"
        echo "@SET \"_CONDA_EXE=$win_conda_exe\"" > "$prefix/Library/bin/conda.bat"
        cat "$src_dir/shell/Library/bin/conda.bat" >> "$prefix/Library/bin/conda.bat"
    fi

    mkdir -p "$prefix/etc/fish/conf.d/"
    rm -f "$prefix/etc/fish/conf.d/conda.fish"
    cp "$src_dir/shell/etc/fish/conf.d/conda.fish" "$prefix/etc/fish/conf.d/conda.fish"

    local sp_dir=$("$PYTHON_EXE" -c "from distutils.sysconfig import get_python_lib as g; print(g())")
    mkdir -p "$sp_dir/xonsh"
    rm -f "$sp_dir/xonsh/conda.xsh"
    echo "_CONDA_EXE = \"$CONDA_EXE\"" > "$sp_dir/xonsh/conda.xsh"
    cat "$src_dir/shell/conda.xsh" >> "$sp_dir/xonsh/conda.xsh"

}


make_conda_entrypoint() {
    local filepath="$1"
    local pythonpath="$2"
    local workingdir="$3"
    local function_import="$4"
    rm -f $filepath
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

    if [ -n "$ON_WIN" ]; then
        $PYTHON_EXE utils/setup-testing.py develop  # this, just for the conda.exe and conda-env.exe file
        make_conda_entrypoint "$prefix/Scripts/conda-script.py" "$(cygpath -w "$PYTHON_EXE")" "$(cygpath -w "$src_dir")" "from conda.cli import main"
        make_conda_entrypoint "$prefix/Scripts/conda-env-script.py" "$(cygpath -w "$PYTHON_EXE")" "$(cygpath -w "$src_dir")" "from conda_env.cli.main import main"
    else
        $PYTHON_EXE setup.py develop
        make_conda_entrypoint "$CONDA_EXE" "$PYTHON_EXE" "$src_dir" "from conda.cli import main"
        make_conda_entrypoint "$prefix/bin/conda-env" "$PYTHON_EXE" "$src_dir" "from conda.cli import main"
    fi

    install_conda_shell_scripts "$prefix" "$src_dir"

    mkdir -p $prefix/conda-meta
    touch $prefix/conda-meta/history

    $CONDA_EXE info

    $CONDA_EXE config --set auto_update_conda false
}


install_conda_dev_usr_local() {
    sudo -E bash -c "source utils/functions.sh && install_conda_dev /usr/local"
    sudo chown -R root:root ./conda
    ls -al ./conda
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
    $prefix/bin/pip install --no-deps .
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


conda_unit_test() {
    $PYTHON_EXE utils/setup-testing.py --version
    $PYTEST_EXE $ADD_COV -m "not integration and not installed"
}


conda_integration_test() {
    $PYTEST_EXE $ADD_COV -m "integration and not installed"
}


conda_activate_test() {
    # this hard-codes __version__ in conda/__init__.py to speed up tests
    if [ "$SUDO" = true ]; then
        sudo $PYTHON_EXE -m conda._vendor.auxlib.packaging conda
    else
        $PYTHON_EXE -m conda._vendor.auxlib.packaging conda
    fi

    $PYTHON_EXE -c "import conda; print(conda.__version__)"
    $CONDA_EXE info

    if [ -n "$ON_WIN" ]; then
        $PYTEST_EXE $ADD_COV -m "installed" --shell=bash.exe --shell=cmd.exe
    else
        $PYTEST_EXE $ADD_COV -m "installed" --shell=bash --shell=zsh  # --shell=dash
    fi

}


conda_build_smoke_test() {
    local prefix=${1:-$INSTALL_PREFIX}

    $prefix/$BIN_DIR/conda config --add channels conda-canary
    $prefix/$BIN_DIR/conda build conda.recipe
}


conda_build_test() {
    local prefix=${1:-$INSTALL_PREFIX}

    echo
    echo ">>>>>>>>>>>> running conda-build unit tests >>>>>>>>>>>>>>>>>>>>>"
    echo

    export PATH="$prefix/bin:$PATH"  # cheating
    conda info

    pushd conda-build

    # TODO: remove -k flag when conda/conda-build#1927 is merged
    $prefix/$BIN_DIR/python -m pytest --basetemp /tmp/cb -v --durations=20 -n 2 -m "not serial" tests \
        -k "not xattr"
    $prefix/$BIN_DIR/python -m pytest --basetemp /tmp/cb -v --durations=20 -n 0 -m "serial" tests
    popd
}


run_setup() {
    set -e
    set -x
    env | sort

    case "$(uname -s)" in
        'Darwin')
            install_conda_dev
            ;;
        'Linux')
            if [[ $FLAKE8 == true ]]; then
                pip install flake8
            elif [[ $SUDO == true ]]; then
                install_conda_dev_usr_local
            elif [[ -n $CONDA_BUILD ]]; then
                install_conda_build
            else
                install_conda_dev
            fi
            ;;
        CYGWIN*|MINGW*|MSYS*)
            install_conda_dev
            ;;
        *)  echo "setup not configured for $(uname -s)"
            return 1
            ;;
    esac

    set +e
    set +x
}


run_tests() {
    set -e
    if [ "$FLAKE8" = true ]; then
        flake8 --statistics
    elif [ -n "$CONDA_BUILD" ]; then
        # conda_build_smoke_test
        conda_build_test
    elif [ -n "$SHELL_INTEGRATION" ]; then
        conda_unit_test
        conda_activate_test
        # $INSTALL_PREFIX/$BIN_DIR/codecov --env PYTHON_VERSION --flags activate --required
    else
        conda_unit_test
        conda_integration_test
        $INSTALL_PREFIX/$BIN_DIR/codecov --env PYTHON_VERSION --flags integration --required
    fi
}

set_vars
set_test_vars
