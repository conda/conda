#!/usr/bin/env bash

set -o errtrace -o pipefail -o errexit

eval "$(sudo /opt/conda/bin/python -m conda init --dev bash)"
sudo su root -c "/opt/conda/bin/conda install -yq conda-build conda-forge::pytest-split"
conda-build tests/test-recipes/activate_deactivate_package

# remove the pkg cache.  We can't hardlink from here anyway.  Having it around causes log problems.
sudo rm -rf /opt/conda/pkgs/*-*-*

pytest -v --splits 4 --group ${TEST_GROUP} --store-durations --basetemp=tests/out
python -m conda.common.io
