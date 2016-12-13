set -e
set +x

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
    export PYTHONHASHSEED=$(python -c "import random as r; print(r.randint(0,4294967296))")
    echo $PYTHONHASHSEED

    # basic unit tests
    python -m pytest --cov-report xml --shell=bash --shell=zsh -m "not installed" tests
    python utils/setup-testing.py --version
}

activate_test() {
#    local prefix=$(python -c "import sys; print(sys.prefix)")
#    ln -sf shell/activate $prefix/bin/activate
#    ln -sf shell/deactivate $prefix/bin/deactivate
#    make_conda_entrypoint $prefix/bin/conda $prefix/bin/python pwd

    python utils/setup-testing.py develop
    hash -r
    which conda
    python -m conda info
    python -m pytest --cov-report term-missing --cov-report xml --cov-append --shell=bash --shell=zsh -m "installed" tests
}

flake8_test() {
    python -m flake8 --statistics
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
    python -m pytest -n 2 --basetemp /tmp/cb tests || echo -e "\n>>>>> conda-build tests exited with code" $? "\n\n\n"
    popd
}

which -a python
env | sort

if [[ $FLAKE8 == true ]]; then
    flake8_test
elif [[ -n $CONDA_BUILD ]]; then
    conda_build_smoke_test
    conda_build_unit_test
    # if [[ $CONDA_BUILD == 1.21.11 || $CONDA_BUILD == master ]]; then
    # fi
else
    main_test
    if [[ "$(uname -s)" == "Linux" ]]; then
        activate_test
    fi
fi
