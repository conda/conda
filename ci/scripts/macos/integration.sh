#!/usr/bin/env bash

set -o errtrace -o pipefail -o errexit

CONDA="${CONDA:-/usr/local/miniconda}"

eval "$(sudo ${CONDA}/bin/python -m conda init --dev bash)"
conda-build tests/test-recipes/activate_deactivate_package
pytest -m "integration" -v --splits ${TEST_SPLITS} --group=${TEST_GROUP}
python -m conda.common.io
