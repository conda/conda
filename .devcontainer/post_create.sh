#!/bin/bash

set -euo pipefail

CONDA_SRC=${CONDA_SRC:-/workspaces/conda}

/opt/conda/bin/conda install -n base --yes --quiet \
    --override-channels --channel=defaults \
    --file=${CONDA_SRC}/requirements/runtime.txt \
    --file=${CONDA_SRC}/requirements/tests.txt \
    --file=${CONDA_SRC}/requirements/Linux.txt \
    --file=${CONDA_SRC}/requirements/s3.txt \
    --file=${CONDA_SRC}/requirements/devcontainer.txt
