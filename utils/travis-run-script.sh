set -e
set -x

main_test() {
    export PYTHONHASHSEED=$(python -c "import random as r; print(r.randint(0,4294967296))")
    echo $PYTHONHASHSEED
    $PYTHON_EXE -m py.test --cov-report xml --shell=bash --shell=zsh -m "not installed" tests
    $PYTHON_EXE setup.py --version
    $PYTHON_EXE setup.py install
    hash -r
    conda info
    $PYTHON_EXE -m py.test --cov-report xml --cov-append --shell=bash --shell=zsh -m "installed" tests
    # conda install -y -q conda-build
    # set +x
    # conda build conda.recipe
}

flake8_test() {
    flake8 --statistics
}

which -a python
env | sort

if [[ $FLAKE8 == true ]]; then
    flake8_test
else
    main_test
fi
