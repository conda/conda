#!/bin/bash

set -euo pipefail

CONDA_SRC=${CONDA_SRC:-/workspaces/conda}

PRE314=
if /opt/conda/bin/python -c 'import sys; sys.exit(0 if sys.version_info < (3, 14) else 1)'; then
    PRE314="--file=${CONDA_SRC}/tests/requirements-pre314.txt"
fi

/opt/conda/bin/conda install -n base --yes --quiet \
    --override-channels --channel=defaults \
    --file=${CONDA_SRC}/tests/requirements.txt \
    --file=${CONDA_SRC}/tests/requirements-ci.txt \
    --file=${CONDA_SRC}/tests/requirements-Linux.txt \
    --file=${CONDA_SRC}/tests/requirements-s3.txt \
    --file=${CONDA_SRC}/.devcontainer/requirements-dev.txt \
    ${PRE314}
