#!/usr/bin/env bash

set -o errtrace -o pipefail -o errexit

GROUP_COUNT="${GROUP_COUNT:-1}"
TEST_GROUP="${TEST_GROUP:-1}"

eval "$(sudo /opt/conda/bin/python -m conda init --dev bash)"
sudo su root -c "/opt/conda/bin/conda install -yq conda-build"
conda-build tests/test-recipes/activate_deactivate_package
pytest -m "integration and not installed" -v --splits ${GROUP_COUNT} --group=${TEST_GROUP}
python -m conda.common.io
