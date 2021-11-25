#!/usr/bin/env bash

set -o errtrace -o pipefail -o errexit

conda install -yq pip conda-build conda-verify pytest
conda update openssl ca-certificates certifi
eval "$(python -m conda init bash --dev)"
