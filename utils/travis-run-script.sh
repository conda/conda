set -e
set -x

main_test() {
    export PYTHONHASHSEED=$(python -c "import random as r; print(r.randint(0,4294967296))")
    echo $PYTHONHASHSEED

    # basic unit tests
    python -m pytest --cov-report xml --shell=bash --shell=zsh -m "not installed" tests
    python setup.py --version

    # activate tests
    python setup.py install
    hash -r
    python -m conda info
    python -m pytest --cov-report xml --cov-append --shell=bash --shell=zsh -m "installed" tests

    # conda-build smoke test
    python -m conda config --set auto_update_conda false
    python -m conda install -y -q conda-build
    python -m conda build conda.recipe
}

flake8_test() {
    python -m flake8 --statistics
}

which -a python
env | sort

if [[ $FLAKE8 == true ]]; then
    flake8_test
else
    main_test
fi
