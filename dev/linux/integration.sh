#!/usr/bin/env bash

set -o errtrace -o pipefail -o errexit

TEST_SPLITS="${TEST_SPLITS:-1}"
TEST_GROUP="${TEST_GROUP:-1}"

sudo su root -c "/opt/conda/bin/conda install -yq conda-build"
# make sure all test requirements are installed
sudo /opt/conda/bin/conda install --quiet -y -c defaults --file tests/requirements.txt
conda info
eval "$(sudo /opt/conda/bin/python -m conda init --dev bash)"
conda-build tests/test-recipes/activate_deactivate_package tests/test-recipes/pre_link_messages_package
pytest -m "integration" -v --splits ${TEST_SPLITS} --group=${TEST_GROUP}
python -m conda.common.io
