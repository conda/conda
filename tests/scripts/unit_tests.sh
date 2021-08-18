#!/usr/bin/env bash

set -o errtrace -o pipefail -o errexit

GROUP_COUNT="${GROUP_COUNT:-1}"
TEST_GROUP="${TEST_GROUP:-1}"

eval "$(sudo /opt/conda/bin/python -m conda init --dev bash)"
conda info
sudo su root -c "/opt/conda/bin/conda install -yq conda-forge::pytest-split"
# remove the pkg cache.  We can't hardlink from here anyway.  Having it around causes log problems.
sudo rm -rf /opt/conda/pkgs/*-*-*
pytest -m "not integration and not installed" -vv --splits ${GROUP_COUNT} --group=${TEST_GROUP}
