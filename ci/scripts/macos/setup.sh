#!/usr/bin/env bash

set -o errtrace -o pipefail -o errexit

CONDA="${CONDA:-/usr/local/miniconda}"

${CONDA}/bin/conda create -n conda-test-env -y python=${PYTHON} --file=tests/requirements.txt
${CONDA}/bin/conda activate conda-test-env
${CONDA}/bin/conda install -yq pip conda-build conda-verify
${CONDA}/bin/conda update openssl ca-certificates certifi
${CONDA}/bin/python -m conda init cmd.exe --dev
