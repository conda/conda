#!/usr/bin/env bash

set -o errtrace -o pipefail -o errexit

conda install -yq pip conda-build conda-verify
conda update openssl ca-certificates certifi
python -m conda init bash --dev
