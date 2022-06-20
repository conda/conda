FROM debian:buster-slim AS buildbase

ARG CONDA_VERSION=latest

WORKDIR /tmp

RUN apt-get update && apt-get install -y wget

RUN set -x && \
    UNAME_M="$(uname -m)" && \
    if [ "${UNAME_M}" = "x86_64" ]; then \
        MINICONDA_URL="https://repo.anaconda.com/miniconda/Miniconda3-${CONDA_VERSION}-Linux-x86_64.sh"; \
    elif [ "${UNAME_M}" = "s390x" ]; then \
        MINICONDA_URL="https://repo.anaconda.com/miniconda/Miniconda3-${CONDA_VERSION}-Linux-s390x.sh"; \
    elif [ "${UNAME_M}" = "aarch64" ]; then \
        MINICONDA_URL="https://repo.anaconda.com/miniconda/Miniconda3-${CONDA_VERSION}-Linux-aarch64.sh"; \
    elif [ "${UNAME_M}" = "ppc64le" ]; then \
        MINICONDA_URL="https://repo.anaconda.com/miniconda/Miniconda3-${CONDA_VERSION}-Linux-ppc64le.sh"; \
    fi && \
    wget --quiet $MINICONDA_URL -O ~/miniconda.sh && \
    /bin/bash ~/miniconda.sh -b -p /opt/conda && \
    rm ~/miniconda.sh && \
    /opt/conda/bin/conda clean --all --yes

FROM debian:buster-slim

ENV LANG=C.UTF-8 LC_ALL=C.UTF-8
ENV PATH /opt/conda/bin:$PATH

COPY dev/linux/setup.sh /tmp
RUN bash /tmp/setup.sh

COPY --from=buildbase /opt/conda /opt/conda

ARG python_version=3.9

COPY ./tests/requirements.txt /tmp

# conda and test dependencies
RUN /opt/conda/bin/conda install --update-all -y -c defaults \
    python=$python_version \
    --file /tmp/requirements.txt && \
    /opt/conda/bin/conda clean --all --yes

# Make /opt/conda world-writable to allow hardlinks during tests
RUN chmod -R o+w /opt/conda/pkgs/*-*-*

USER test_user

WORKDIR /opt/conda-src

ENTRYPOINT ["/usr/bin/tini", "--"]
CMD ["/bin/bash"]
