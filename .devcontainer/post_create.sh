#!/bin/bash

set -euo pipefail

CONDA_SRC=${CONDA_SRC:-/workspaces/conda}

/opt/conda/bin/conda install -n base --yes --quiet conda-forge::conda-workspaces

cd "${CONDA_SRC}"
/opt/conda/bin/conda workspace install -e default --yes
/opt/conda/bin/conda workspace install -e s3 --yes
/opt/conda/bin/conda workspace install -e lint --yes
