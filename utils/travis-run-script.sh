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

conda_build_smoke_test() {
    python setup.py install
    conda install -y -q jinja2 patchelf
    pip install git+https://github.com/conda/conda-build.git@$CONDA_BUILD
    conda info
    conda config --add channels conda-canary
    conda build conda.recipe
}

conda_build_unit_test() {
    git clone -b $CONDA_BUILD --single-branch --depth 1000 https://github.com/conda/conda-build.git
    pushd conda-build
    python setup.py install
    conda install -y -q pytest pytest-cov mock anaconda-client
    python -m pytest tests
}

which -a python
env | sort

if [[ $FLAKE8 == true ]]; then
    flake8_test
elif [[ -n $CONDA_BUILD ]]; then
    conda_build_smoke_test
    if [[ $CONDA_BUILD == master ]]; then
        conda_build_unit_test
    fi
else
    main_test
fi
