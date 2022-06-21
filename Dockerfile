# This a Dockerfile with multi-platform support, build (pull/run) it via:
# * Setup qemu for non-native platforms (to be done once):
#       `docker run --privileged --rm tonistiigi/binfmt --install all`
# * Setup buildx as default docker builder (to be done once):
#       `docker buildx install`
# * Build with without `--platform ...` arg (TARGETPLATFORM=BUILDPLATFORM):
#       `docker build .`
# * Build a single platform image:
#       `docker build --platform linux/amd64 .`
# * Build a multi-platform image:
#       `docker build --platform linux/amd64,linux/arm64 .`
# See also:
# * https://docs.docker.com/buildx/working-with-buildx/
# * https://www.docker.com/blog/faster-multi-platform-builds-dockerfile-cross-compilation-guide/

# built-in arg set via `docker build --platform $TARGETPLATFORM ...` or TARGETPLATFORM=BUILDPLATFORM
FROM --platform=$TARGETPLATFORM debian:buster-slim AS buildbase

# built-in arg set by `docker build --platform linux/$TARGETARCH ...`
ARG TARGETARCH
ARG CONDA_VERSION=latest

WORKDIR /tmp

RUN apt-get update && apt-get install -y wget

RUN if [ "${TARGETARCH}" = "amd64" ]; then \
        MINICONDA_URL="https://repo.anaconda.com/miniconda/Miniconda3-${CONDA_VERSION}-Linux-x86_64.sh"; \
    elif [ "${TARGETARCH}" = "s390x" ]; then \
        MINICONDA_URL="https://repo.anaconda.com/miniconda/Miniconda3-${CONDA_VERSION}-Linux-s390x.sh"; \
    elif [ "${TARGETARCH}" = "arm64" ]; then \
        MINICONDA_URL="https://repo.anaconda.com/miniconda/Miniconda3-${CONDA_VERSION}-Linux-aarch64.sh"; \
    elif [ "${TARGETARCH}" = "ppc64le" ]; then \
        MINICONDA_URL="https://repo.anaconda.com/miniconda/Miniconda3-${CONDA_VERSION}-Linux-ppc64le.sh"; \
    else \
        echo "Not supported target architecture: ${TARGETARCH}"; \
        exit 1; \
    fi && \
    wget --quiet $MINICONDA_URL -O ~/miniconda.sh && \
    /bin/bash ~/miniconda.sh -b -p /opt/conda && \
    rm ~/miniconda.sh && \
    /opt/conda/bin/conda clean --all --yes

FROM --platform=$TARGETPLATFORM debian:buster-slim

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
