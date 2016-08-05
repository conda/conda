set -e
set -x

main_test() {
    export PYTHONHASHSEED=$(python -c "import random as r; print(r.randint(0,4294967296))")
    echo $PYTHONHASHSEED
    python -m pytest --cov-report xml --shell=bash --shell=zsh --shell=dash --shell=sh --shell=csh --shell=tcsh -m "not installed" tests
    python setup.py --version
    python setup.py install
    hash -r
    python -m conda info
    python -m pytest --cov-report xml --cov-append --shell=bash --shell=zsh  --shell=dash --shell=sh --shell=csh --shell=tcsh -m "installed" tests
    # python -m conda install -y -q conda-build
    # set +x
    # python -m conda build conda.recipe
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
