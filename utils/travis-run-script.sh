set -e
set -x

main_test() {
    export PYTHONHASHSEED=$(python -c "import random as r; print(r.randint(0,4294967296))")
    echo $PYTHONHASHSEED

    case "$(uname -s)" in
        'Darwin') shells="";;
        'Linux') shells="";; # "--shell=posh";;
        *) ;;
    esac
    shells="$shells --shell=bash --shell=zsh --shell=dash --shell=sh --shell=csh --shell=tcsh"

    echo "PRE-INSTALL CONDA TESTS"
    python -m pytest --cov-report xml $shells -m "not installed" tests

    echo "INSTALL CONDA"
    python setup.py --version

    # activate tests
    python setup.py install
    hash -r
    python -m conda info

    echo "POST-INSTALL CONDA TESTS"
    python -m pytest --cov-report xml --cov-append $shells -m "installed" tests
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
    python -m pytest tests || echo ">>> exited with code" $?
    popd
}

if [[ $FLAKE8 == true ]]; then
    flake8_test
elif [[ -n $CONDA_BUILD ]]; then
    conda_build_smoke_test
    if [[ $CONDA_BUILD == 1.21.11 || $CONDA_BUILD == master ]]; then
        conda_build_unit_test
    fi
else
    main_test
fi
