#!/usr/bin/env bash

set -o errtrace -o pipefail -o errexit

### Prevent git safety errors when mounting directories ###
git config --global --add safe.directory /opt/conda-src

TEST_SPLITS="${TEST_SPLITS:-1}"
TEST_GROUP="${TEST_GROUP:-1}"

# make sure all test requirements are installed
sudo /opt/conda/bin/conda install --quiet -y --file tests/requirements.txt
# TODO:  Remove before merge, temporary:
sudo su root -c "/opt/conda/bin/conda install -yq jaimergp/label/menuinst_dev::menuinst=2 --no-deps"
eval "$(sudo /opt/conda/bin/python -m conda init --dev bash)"
conda info
# remove the pkg cache.  We can't hardlink from here anyway.  Having it around causes log problems.
sudo rm -rf /opt/conda/pkgs/*-*-*
# put temporary files on same filesystem
export TMP=$HOME/pytesttmp
mkdir -p $TMP
python -m pytest --cov=conda --store-durations --durations-path=./tools/durations/${OS}.json --splitting-algorithm=least_duration --basetemp=$TMP -m "not integration" -v --splits ${TEST_SPLITS} --group=${TEST_GROUP}
