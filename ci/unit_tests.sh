if [[ $(git diff origin/master --name-only | wc -l) == $(git diff origin/master --name-only | grep docs | wc -l) && $(git diff origin/master --name-only | grep docs) ]]; then
    echo "Only docs changed detected, skipping tests"
else
    eval "$(sudo /opt/conda/bin/python -m conda init --dev bash)"
    conda info
    # remove the pkg cache.  We can't hardlink from here anyway.  Having it around causes log problems.
    sudo rm -rf /opt/conda/pkgs/*-*-*
    py.test $ADD_COV -m "not integration and not installed" -v
fi
