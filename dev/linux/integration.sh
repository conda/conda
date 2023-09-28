#!/usr/bin/env bash

set -o errtrace -o pipefail -o errexit

### Prevent git safety errors when mounting directories ###
git config --global --add safe.directory /opt/conda-src

TEST_SPLITS="${TEST_SPLITS:-1}"
TEST_GROUP="${TEST_GROUP:-1}"

# make sure all test requirements are installed
sudo /opt/conda/bin/conda install --quiet -y --file tests/requirements.txt --file tests/requirements-extra.txt
eval "$(sudo /opt/conda/bin/python -m conda init --dev bash)"
conda info
# put temporary files on same filesystem
export TMP=$HOME/pytesttmp
mkdir -p $TMP
python -m pytest \
    --cov=conda \
    --durations-path=./tools/durations/${OS}.json \
    --basetemp=$TMP \
    -m "integration" \
    --splits=${TEST_SPLITS} \
    --group=${TEST_GROUP}
python -m conda.common.io
