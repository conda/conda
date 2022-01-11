#!/usr/bin/env bash

set -o errtrace -o pipefail -o errexit

TEST_SPLITS="${TEST_SPLITS:-1}"
TEST_GROUP="${TEST_GROUP:-1}"

eval "$(sudo python -m conda init bash --dev)"
conda info
mamba --version
CONDA_SOLVER_LOGIC=libmamba2 pytest \
    -m "not integration" -k "not TestClassicSolver" \
    -v --splits ${TEST_SPLITS} --group=${TEST_GROUP} \
    tests/core/test_solve.py \
    tests/test_solvers.py
