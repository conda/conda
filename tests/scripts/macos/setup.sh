#!/usr/bin/env bash

set -o errtrace -o pipefail -o errexit

PYTHON="${PYTHON:-3.8}"

conda activate base
conda create -n conda-test-env -y --channel defaults python=${PYTHON} --file=tests/requirements.txt
conda activate conda-test-env
conda install -yq pip conda-build conda-verify
conda update openssl ca-certificates certifi
eval "$(conda init --dev bash)"
