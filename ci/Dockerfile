FROM debian:buster-slim

ENV LANG=C.UTF-8 LC_ALL=C.UTF-8
ENV PATH /opt/conda/bin:$PATH

# hadolint ignore=DL3008
RUN apt-get update --fix-missing && \
    apt-get install -y --no-install-recommends wget build-essential bzip2 ca-certificates libglib2.0-0 libxext6 libsm6 libxrender1 git mercurial subversion sudo && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/* && \
    useradd -m -s /bin/bash test_user && \
    usermod -u 1001 test_user && \
    groupmod -g 1001 test_user && \
    echo "test_user ALL=(ALL) NOPASSWD:ALL" >> /etc/sudoers && \
    wget --quiet https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh -O ~/miniconda.sh && \
    /bin/bash ~/miniconda.sh -b -p /opt/conda && \
    rm ~/miniconda.sh && \
    /opt/conda/bin/conda clean -tipsy

ARG PYTHON_VERSION=3.8

# conda and test dependencies
RUN /opt/conda/bin/conda install --update-all -y -c defaults \
    conda conda-package-handling \
    python=$PYTHON_VERSION pip pycosat requests ruamel_yaml cytoolz \
    anaconda-client nbformat make \
    pytest pytest-cov codecov radon pytest-timeout mock responses pexpect \
    flake8 && \
    /opt/conda/bin/conda clean --all --yes

# conda-build and test dependencies
RUN /opt/conda/bin/conda install --update-all -y -c defaults \
        conda-build patch git \
        perl pytest-xdist pytest-mock \
        anaconda-client \
        filelock jinja2 conda-verify pkginfo \
        glob2 beautifulsoup4 chardet pycrypto \
    && /opt/conda/bin/conda clean --all --yes

USER test_user

ENTRYPOINT [ "/bin/bash" ]
