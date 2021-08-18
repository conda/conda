#!/usr/bin/env bash

set -o errtrace -o pipefail -o errexit

TEST_SPLITS="${TEST_SPLITS:-1}"
TEST_GROUP="${TEST_GROUP:-1}"

conda run --name conda-tests conda-build tests/test-recipes/activate_deactivate_package
conda run --name conda-tests pytest -m "integration and not installed" -v --splits ${TEST_SPLITS} --group=${TEST_GROUP}
conda run --name conda-tests python -m conda.common.io
