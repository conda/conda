FROM debian:buster-slim AS buildbase

ARG MINICONDA_URL=https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh

WORKDIR /tmp

RUN apt-get update && apt-get install -y wget

RUN wget --quiet $MINICONDA_URL -O ~/miniconda.sh && \
    /bin/bash ~/miniconda.sh -b -p /opt/conda && \
    rm ~/miniconda.sh && \
    /opt/conda/bin/conda clean --all --yes

FROM debian:buster-slim

ENV LANG=C.UTF-8 LC_ALL=C.UTF-8
ENV PATH /opt/conda/bin:$PATH

COPY ci/scripts/linux/setup.sh /tmp
RUN bash /tmp/setup.sh

COPY --from=buildbase /opt/conda /opt/conda

ARG PYTHON_VERSION=3.8

COPY tests/requirements.txt /tmp

# conda and test dependencies
RUN /opt/conda/bin/conda install --update-all -y -c defaults \
    python=$PYTHON_VERSION \
    --file /tmp/requirements.txt && \
    /opt/conda/bin/conda clean --all --yes

USER test_user

WORKDIR /opt/conda-src

ENTRYPOINT ["/usr/bin/tini", "--"]
CMD ["/bin/bash"]
