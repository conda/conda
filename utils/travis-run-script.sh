set -e
set +x

main_test() {
    echo "MAIN TEST ($(pwd))"

    export PYTHONHASHSEED=$(python -c "import random as r; print(r.randint(0,4294967296))")
    echo $PYTHONHASHSEED

    # detect what shells are available to test with
    # don't bother testing for the default shell `sh`, generally speaking the default
    # shell will be supported if it's one of the supported shells
    shells=""
    [[ $(which -s bash) ]] || shells="${shells} --shell=bash"
    [[ $(which -s dash) ]] || shells="${shells} --shell=dash"
    [[ $(which -s posh) ]] || shells="${shells} --shell=posh"
    [[ $(which -s zsh) ]]  || shells="${shells} --shell=zsh"
    [[ $(which -s csh) ]]  || shells="${shells} --shell=csh"
    [[ $(which -s tcsh) ]] || shells="${shells} --shell=tcsh"

    echo "PRE-INSTALL CONDA TESTS"
    python -m pytest --cov-report xml $shells -m "not installed" tests

    echo "INSTALL CONDA"
    python setup.py --version
    python setup.py install
    hash -r
    python -m conda info

    echo "POST-INSTALL CONDA TESTS"
    python -m pytest --cov-report xml --cov-append $shells -m "installed" tests

    echo "END MAIN TEST ($(pwd))"
}

flake8_test() {
    echo "FLAKE8 TEST ($(pwd))"

    python -m flake8 --statistics

    echo "END FLAKE8 TEST ($(pwd))"
}

conda_build_smoke_test() {
    echo "CONDA BUILD SMOKE TEST ($(pwd))"

    conda config --add channels conda-canary
    conda build conda.recipe

    echo "END CONDA BUILD SMOKE TEST ($(pwd))"
}

conda_build_unit_test() {
    echo "CONDA BUILD UNIT TEST ($(pwd))"

    pushd conda-build
    echo
    echo ">>>>>>>>>>>> runnin conda-build unit tests >>>>>>>>>>>>>>>>>>>>>"
    echo
    python -m pytest -n 2 --basetemp /tmp/cb tests || echo -e "\n>>>>> conda-build tests exited with code" $? "\n\n\n"
    popd

    echo "END CONDA BUILD UNIT TEST ($(pwd))"
}

if [[ $FLAKE8 == true ]]; then
    flake8_test
elif [[ -n $CONDA_BUILD ]]; then
    conda_build_smoke_test
    conda_build_unit_test
else
    main_test
fi
