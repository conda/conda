#!/usr/bin/env bash

set -o errtrace -o pipefail -o errexit

TEST_SPLITS="${TEST_SPLITS:-1}"
TEST_GROUP="${TEST_GROUP:-1}"

eval "$(sudo /opt/conda/bin/python -m conda init --dev bash)"
conda info
mamba --version
# remove the pkg cache.  We can't hardlink from here anyway.  Having it around causes log problems.
sudo rm -rf /opt/conda/pkgs/*-*-*
CONDA_SOLVER_LOGIC=libmamba pytest \
    -m "not integration" -k "not TestClassicSolver" \
    -v --splits ${TEST_SPLITS} --group=${TEST_GROUP} \
    tests/core/test_solve.py \
    tests/test_solvers.py
