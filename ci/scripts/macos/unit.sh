#!/usr/bin/env bash

set -o errtrace -o pipefail -o errexit

CONDA="${CONDA:-/usr/local/miniconda}"

eval "$(sudo ${CONDA}/bin/python -m conda init --dev bash)"
conda info
pytest -m "not integration" -v --splits ${TEST_SPLITS} --group=${TEST_GROUP}
