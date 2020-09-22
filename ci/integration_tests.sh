if [[ $(git diff origin/master --name-only | wc -l) == $(git diff origin/master --name-only | grep docs | wc -l) && $(git diff origin/master --name-only | grep docs) ]]; then
    echo "Only docs changed detected, skipping tests"
else
    eval "$(sudo /opt/conda/bin/python -m conda init --dev bash)"
    sudo su root -c "/opt/conda/bin/conda install -yq conda-build"
    conda-build tests/test-recipes/activate_deactivate_package
    py.test $ADD_COV --cov-append -m "integration and not installed" -v
    python -m conda.common.io
fi
