#!/usr/bin/env bash

set -o errtrace -o pipefail -o errexit

TEST_SPLITS="${TEST_SPLITS:-1}"
TEST_GROUP="${TEST_GROUP:-1}"

eval "$(sudo /usr/share/miniconda/bin/python -m conda init --dev bash)"
sudo su root -c "/usr/share/miniconda/bin/conda install -yq conda-build"
conda-build tests/test-recipes/activate_deactivate_package
pytest -m "integration and not installed" -v --splits ${TEST_SPLITS} --group=${TEST_GROUP}
python -m conda.common.io
