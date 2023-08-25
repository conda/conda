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
FROM --platform=$TARGETPLATFORM debian:stable-slim AS buildbase

# built-in arg set by `docker build --platform linux/$TARGETARCH ...`
ARG TARGETARCH
ARG CONDA_VERSION=latest
ARG default_channel=defaults

WORKDIR /tmp

RUN apt-get update && apt-get install -y wget

COPY dev/linux/install_miniconda.sh /tmp
RUN bash /tmp/install_miniconda.sh

FROM --platform=$TARGETPLATFORM debian:stable-slim

ENV LANG=C.UTF-8 LC_ALL=C.UTF-8
ENV PATH /opt/conda/bin:$PATH

COPY dev/linux/setup.sh /tmp
RUN bash /tmp/setup.sh

COPY --from=buildbase /opt/conda /opt/conda

ARG python_version=3.9

COPY ./tests/requirements.txt /tmp

# conda and test dependencies
RUN /opt/conda/bin/conda install --update-all -y \
    python=$python_version \
    --file /tmp/requirements.txt && \
    /opt/conda/bin/conda clean --all --yes

# Make /opt/conda world-writable to allow hardlinks during tests
RUN chmod -R o+w /opt/conda/pkgs/*-*-*

USER test_user

WORKDIR /opt/conda-src

ENTRYPOINT ["/usr/bin/tini", "--"]
CMD ["/bin/bash"]
