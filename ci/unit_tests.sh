#!/usr/bin/env bash

set -o errtrace -o pipefail -o errexit

eval "$(sudo /opt/conda/bin/python -m conda init --dev bash)"
conda info
# remove the pkg cache.  We can't hardlink from here anyway.  Having it around causes log problems.
sudo rm -rf /opt/conda/pkgs/*-*-*
pytest -m "not integration and not installed" -v
