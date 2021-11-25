#!/usr/bin/env bash

set -o errtrace -o pipefail -o errexit

conda-build tests/test-recipes/activate_deactivate_package
pytest -m "integration" -v --splits ${TEST_SPLITS} --group=${TEST_GROUP}
python -m conda.common.io
