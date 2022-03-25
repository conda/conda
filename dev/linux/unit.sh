#!/usr/bin/env bash

set -o errtrace -o pipefail -o errexit

TEST_SPLITS="${TEST_SPLITS:-1}"
TEST_GROUP="${TEST_GROUP:-1}"

eval "$(sudo /opt/conda/bin/python -m conda init --dev bash)"
conda info
# TODO:  Remove before merge, temporary:
sudo su root -c "/opt/conda/bin/conda install -yq -c jaimergp/label/menuinst_dev -c conda-forge menuinst=2"
# remove the pkg cache.  We can't hardlink from here anyway.  Having it around causes log problems.
sudo rm -rf /opt/conda/pkgs/*-*-*
pytest -m "not integration" -v --splits ${TEST_SPLITS} --group=${TEST_GROUP}
