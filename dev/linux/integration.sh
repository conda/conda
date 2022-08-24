#!/usr/bin/env bash

set -o errtrace -o pipefail -o errexit

TEST_SPLITS="${TEST_SPLITS:-1}"
TEST_GROUP="${TEST_GROUP:-1}"

sudo su root -c "/opt/conda/bin/conda install -yq conda-build"
eval "$(sudo /opt/conda/bin/python -m conda init --dev bash)"
conda-build tests/test-recipes/activate_deactivate_package tests/test-recipes/pre_link_messages_package
conda info
pytest -m "integration" --basetemp=$HOME/.conda/tmp-$(date -Iseconds) -v --splits ${TEST_SPLITS} --group=${TEST_GROUP}
python -m conda.common.io
