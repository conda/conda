#!/usr/bin/env bash

set -o errtrace -o pipefail -o errexit

TEST_SPLITS="${TEST_SPLITS:-1}"
TEST_GROUP="${TEST_GROUP:-1}"

eval "$(sudo /opt/conda/bin/python -m conda init --dev bash)"
# make sure all test requirements are installed
sudo /opt/conda/bin/conda install --quiet -y -c defaults --file tests/requirements.txt
conda info
# remove the pkg cache.  We can't hardlink from here anyway.  Having it around causes log problems.
sudo rm -rf /opt/conda/pkgs/*-*-*
# put temporary files on same filesystem
export TMP=$HOME/pytesttmp
mkdir -p $TMP
pytest --basetemp=$TMP -m "not integration" -v --splits ${TEST_SPLITS} --group=${TEST_GROUP}
