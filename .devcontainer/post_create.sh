#!/bin/bash

set -euo pipefail

CONDA_SRC=${CONDA_SRC:-/workspaces/conda}

/opt/conda/bin/conda install -n base --yes --quiet \
    --override-channels --channel=defaults \
    --file=${CONDA_SRC}/tests/requirements.txt \
    --file=${CONDA_SRC}/tests/requirements-ci.txt \
    --file=${CONDA_SRC}/tests/requirements-Linux.txt \
    --file=${CONDA_SRC}/tests/requirements-s3.txt \
    --file=${CONDA_SRC}/.devcontainer/requirements-dev.txt
