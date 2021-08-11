#!/usr/bin/env bash

set -o errtrace -o pipefail -o errexit

eval "$(sudo /opt/conda/bin/python -m conda init --dev bash)"
conda info
sudo su root -c "/opt/conda/bin/conda install -yq conda-build conda-forge::pytest-split"
conda-build tests/test-recipes/activate_deactivate_package
# remove the pkg cache.  We can't hardlink from here anyway.  Having it around causes log problems.
sudo rm -rf /opt/conda/pkgs/*-*-*
export PYTHON_VERSION=$(python -c "import sys; print(sys.version.split()[0])")
pytest --store-durations --durations-path "ci/test_durations/py${PYTHON_VERSION}_linux.json"
