set -e
set -x

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

main_test() {
    export PYTEST_EXE="$INSTALL_PREFIX/bin/py.test"
    export PYTHON_EXE=$(sed 's/^\#!//' $PYTEST_EXE | head -1)
    export PYTHON_MAJOR_VERSION=$($PYTHON_EXE -c "import sys; print(sys.version_info[0])")
    export TEST_PLATFORM=$($PYTHON_EXE -c "import sys; print('win' if sys.platform.startswith('win') else 'unix')")
    export PYTHONHASHSEED=$($PYTHON_EXE -c "import random as r; print(r.randint(0,4294967296))")

    export ADD_COV="--cov-report xml --cov-report term-missing --cov-append --cov conda"

    # make conda-version
    $PYTHON_EXE utils/setup-testing.py --version

    # make integration
    $PYTEST_EXE $ADD_COV -m "not integration and not installed"
    $PYTEST_EXE $ADD_COV -m "integration and not installed"

}

activate_test() {
#    local prefix=$(python -c "import sys; print(sys.prefix)")
#    ln -sf shell/activate $prefix/bin/activate
#    ln -sf shell/deactivate $prefix/bin/deactivate
#    make_conda_entrypoint $prefix/bin/conda $prefix/bin/python pwd

    $INSTALL_PREFIX/bin/python utils/setup-testing.py develop
    export PATH="$INSTALL_PREFIX/bin:$PATH"
    hash -r
    $INSTALL_PREFIX/bin/python -c "import conda; print(conda.__version__)"
    $INSTALL_PREFIX/bin/python -m conda info

    export PYTEST_EXE="$INSTALL_PREFIX/bin/py.test"
    # make test-installed
    $PYTEST_EXE $ADD_COV -m "installed"

    $INSTALL_PREFIX/bin/codecov --env PYTHON_VERSION

#    $INSTALL_PREFIX/bin/python -m pytest --cov-report term-missing --cov-report xml --cov-append --shell=bash --shell=zsh -m "installed" tests
}


conda_build_smoke_test() {
    conda config --add channels conda-canary
    conda build conda.recipe
}

conda_build_unit_test() {
    pushd conda-build
    echo
    echo ">>>>>>>>>>>> running conda-build unit tests >>>>>>>>>>>>>>>>>>>>>"
    echo
    $INSTALL_PREFIX/bin/python -m conda info
    $INSTALL_PREFIX/bin/python -m pytest --basetemp /tmp/cb -v --durations=20 -n 0 -m "serial" tests
    $INSTALL_PREFIX/bin/python -m pytest --basetemp /tmp/cb -v --durations=20 -n 2 -m "not serial" tests
    popd
}

env | sort

if [[ $FLAKE8 == true ]]; then
    flake8 --statistics
elif [[ -n $CONDA_BUILD ]]; then
    conda_build_smoke_test
    conda_build_unit_test
else
    main_test
    if [[ "$(uname -s)" == "Linux" ]]; then
        activate_test
    fi
fi

set +x
