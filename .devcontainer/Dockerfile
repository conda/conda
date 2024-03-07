FROM mcr.microsoft.com/devcontainers/miniconda:0-3

COPY tests/requirements.txt \
    tests/requirements-ci.txt \
    tests/requirements-Linux.txt \
    .devcontainer/requirements-dev.txt \
    /tmp/conda-tmp/

RUN umask 0002 \
    && /opt/conda/bin/conda install \
    -n base --yes --quiet --override-channels \
    --channel=defaults \
    --file=/tmp/conda-tmp/requirements.txt \
    --file=/tmp/conda-tmp/requirements-ci.txt \
    --file=/tmp/conda-tmp/requirements-Linux.txt \
    --file=/tmp/conda-tmp/requirements-dev.txt \
    && rm -rf /tmp/conda-tmp
