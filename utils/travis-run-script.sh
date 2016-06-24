set -e
set -x

main_test() {
    export PYTHONHASHSEED=$(python -c "import random as r; print(r.randint(0,4294967296))")
    echo $PYTHONHASHSEED
    py.test --cov-report xml tests --shell=bash --shell=zsh -m "not installed"
    python setup.py install
    conda info
    py.test --cov-report xml tests --shell=bash --shell=zsh -m "installed"
    conda install -y conda-build
    conda build conda.recipe
}

flake8_test() {
    flake8 --statistics
}

if [[ $FLAKE8 == true ]]; then
    flake8_test
else
    main_test
fi
