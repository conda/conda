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
}

flake8_test() {
    python -m flake8 --statistics
}

conda_build_test() {
    python setup.py install
    conda install -y -q jinja2 patchelf
    pip install git+https://github.com/conda/conda-build.git
    conda build conda.recipe
}


which -a python
env | sort

if [[ $FLAKE8 == true ]]; then
    flake8_test
elif [[ $CONDA_BUILD == true ]]; then
    conda_build_test
else
    main_test
fi
