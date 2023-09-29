#!/bin/bash

set -eu

TARGETARCH="${TARGETARCH:-$(uname -m)}"
CONDA_VERSION="${CONDA_VERSION:-latest}"
default_channel="${default_channel:-defaults}"

if [ "${default_channel}" = "defaults" ] || [[ "${default_channel}" = ad-testing/* ]]; then
    if [ "${TARGETARCH}" = "amd64" ]; then
        MINICONDA_URL="https://repo.anaconda.com/miniconda/Miniconda3-${CONDA_VERSION}-Linux-x86_64.sh"
    elif [ "${TARGETARCH}" = "s390x" ]; then
        MINICONDA_URL="https://repo.anaconda.com/miniconda/Miniconda3-${CONDA_VERSION}-Linux-s390x.sh"
    elif [ "${TARGETARCH}" = "arm64" ] || [ "${TARGETARCH}" = "aarch64" ]; then
        MINICONDA_URL="https://repo.anaconda.com/miniconda/Miniconda3-${CONDA_VERSION}-Linux-aarch64.sh"
    elif [ "${TARGETARCH}" = "ppc64le" ]; then
        MINICONDA_URL="https://repo.anaconda.com/miniconda/Miniconda3-${CONDA_VERSION}-Linux-ppc64le.sh"
    else
        echo "Not supported source channel & target architecture: ${default_channel} & ${TARGETARCH}"
        exit 1
    fi
elif [ "${default_channel}" = "conda-forge" ]; then
    if [ "${TARGETARCH}" = "amd64" ]; then
        MINICONDA_URL="https://github.com/conda-forge/miniforge/releases/${CONDA_VERSION}/download/Miniforge3-Linux-x86_64.sh"
    elif [ "${TARGETARCH}" = "arm64" ] || [ "${TARGETARCH}" = "aarch64" ]; then
        MINICONDA_URL="https://github.com/conda-forge/miniforge/releases/${CONDA_VERSION}/download/Miniforge3-Linux-aarch64.sh"
    elif [ "${TARGETARCH}" = "ppc64le" ]; then
        MINICONDA_URL="https://github.com/conda-forge/miniforge/releases/${CONDA_VERSION}/download/Miniforge3-Linux-ppc64le.sh"
    else
        echo "Not supported source channel & target architecture: ${default_channel} & ${TARGETARCH}"
        exit 1
    fi
else
    echo "default_channel value ${default_channel} not supported"
    exit 1
fi

wget --quiet "$MINICONDA_URL" -O ~/miniconda.sh
/bin/bash ~/miniconda.sh -b -p /opt/conda
rm ~/miniconda.sh
/opt/conda/bin/conda clean --all --yes
