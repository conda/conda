#!/usr/bin/env bash

set -o errtrace -o pipefail -o errexit

TEST_SPLITS="${TEST_SPLITS:-1}"
TEST_GROUP="${TEST_GROUP:-1}"

# REMOVE BEFORE MERGE
sudo su root -c "/opt/conda/bin/conda install -yq conda-forge::pytest-xprocess boto3"
# /REMOVE
eval "$(sudo /opt/conda/bin/python -m conda init --dev bash)"
conda info
# remove the pkg cache.  We can't hardlink from here anyway.  Having it around causes log problems.
sudo rm -rf /opt/conda/pkgs/*-*-*
pytest -m "not integration" -v --splits ${TEST_SPLITS} --group=${TEST_GROUP}
