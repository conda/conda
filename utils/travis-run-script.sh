set -e
set -x

main_test() {
    export PYTHONHASHSEED=$(python -c "import random as r; print(r.randint(0,4294967296))")
    echo $PYTHONHASHSEED

    echo "PRE-INSTALL CONDA TESTS"
    python -m pytest --cov-report xml --shell=bash --shell=zsh --shell=dash --shell=sh --shell=csh --shell=tcsh -m "not installed" tests

    echo "INSTALL CONDA"
    python setup.py --version
    python setup.py install
    hash -r
    python -m conda info

    echo "POST-INSTALL CONDA TESTS"
    python -m pytest --cov-report xml --cov-append --shell=bash --shell=zsh  --shell=dash --shell=sh --shell=csh --shell=tcsh -m "installed" tests
    # python -m conda install -y -q conda-build
    # set +x
    # python -m conda build conda.recipe
}

flake8_test() {
    python -m flake8 --statistics
}

if [[ $FLAKE8 == true ]]; then
    flake8_test
else
    main_test
fi
