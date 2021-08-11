#!/usr/bin/env bash

set -o errtrace -o pipefail -o errexit

eval "$(sudo /opt/conda/bin/python -m conda init --dev bash)"
sudo su root -c "/opt/conda/bin/conda install -yq conda-build"
conda-build tests/test-recipes/activate_deactivate_package
pytest $ADD_COV --cov-append -m "integration and not installed" -v
python -m conda.common.io
