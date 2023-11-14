#!/usr/bin/env bash

set -o errtrace -o pipefail -o errexit

### Prevent git safety errors when mounting directories ###
git config --global --add safe.directory /opt/conda-src

# make sure all test requirements are installed
sudo /opt/conda/bin/conda install --quiet -y --file tests/requirements.txt --file tests/requirements-s3.txt
eval "$(sudo /opt/conda/bin/python -m conda init --dev bash)"
conda info
# remove the pkg cache.  We can't hardlink from here anyway.  Having it around causes log problems.
sudo rm -rf /opt/conda/pkgs/*-*-*
# put temporary files on same filesystem
export TMP=$HOME/pytesttmp
mkdir -p "$TMP"
python -m pytest \
    --cov=conda \
    --basetemp="$TMP" \
    tests/test_api.py::test_DepsModifier_contract
