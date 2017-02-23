# Set global variables
case "$(uname -s)" in
    'Darwin')
        export MINICONDA_URL="https://repo.continuum.io/miniconda/Miniconda3-4.2.12-MacOSX-x86_64.sh"
        ;;
    'Linux')
        export MINICONDA_URL="https://repo.continuum.io/miniconda/Miniconda3-4.2.12-Linux-x86_64.sh"
        ;;
    *)  ;;
esac


install_miniconda() {
    local prefix=${1:-$INSTALL_PREFIX}
    curl -sSL $MINICONDA_URL -o ~/miniconda.sh
    chmod +x ~/miniconda.sh
    mkdir -p $prefix
    ~/miniconda.sh -bfp $prefix
}


remove_conda() {
    local prefix=${1:-$INSTALL_PREFIX}
    local site_packages=$($prefix/bin/python -c "from distutils.sysconfig import get_python_lib as g; print(g())")
    rm -rf $prefix/bin/activate \
       $prefix/bin/conda \
       $prefix/bin/conda-env \
       $prefix/bin/deactivate \
       $prefix/conda-meta/conda-*.json \
       $prefix/conda-meta/requests-*.json \
       $prefix/conda-meta/pyopenssl-*.json \
       $prefix/conda-meta/cryptography-*.json \
       $prefix/conda-meta/idna-*.json \
       $prefix/conda-meta/ruamel-*.json \
       $prefix/conda-meta/pycrypto-*.json \
       $prefix/conda-meta/pycosat-*.json \
       $site_packages/conda* \
       $site_packages/requests* \
       $site_packages/pyopenssl* \
       $site_packages/cryptography* \
       $site_packages/idna* \
       $site_packages/ruamel* \
       $site_packages/pycrypto* \
       $site_packages/pycosat*
    hash -r
}


install_python() {
    local prefix=${1:-$INSTALL_PREFIX}
    local python_version=${2:-$PYTHON_VERSION}

    install_miniconda $prefix
    $prefix/bin/conda install -y -q python=$python_version setuptools pip
    remove_conda $prefix

    which python
    $prefix/bin/python --version
    $prefix/bin/pip --version
}


install_conda_dev() {
    local prefix=${1:-$INSTALL_PREFIX}
    install_python $prefix

    $prefix/bin/pip install -r utils/requirements-test.txt
    $prefix/bin/python utils/setup-testing.py develop
    mkdir -p $prefix/conda-meta
    touch $prefix/conda-meta/history

    $prefix/bin/conda info
}


install_conda_build() {
    local prefix=${1:-$INSTALL_PREFIX}

    install_conda_dev $prefix

    # install conda-build test dependencies
    $prefix/bin/conda install -y -q \
        pytest pytest-cov pytest-timeout mock anaconda-client numpy \
        filelock jinja2 patchelf conda-verify contextlib2 pkginfo
    $prefix/bin/conda install -y -q -c conda-forge perl pytest-xdist
    $prefix/bin/pip install pytest-catchlog pytest-mock

    $prefix/bin/conda config --set add_pip_as_python_dependency true

    # install conda-build
    git clone -b $CONDA_BUILD --single-branch --depth 1000 https://github.com/conda/conda-build.git
    local site_packages=$($prefix/bin/python -c "from distutils.sysconfig import get_python_lib as g; print(g())")
    rm -rf $site_packages/conda_build
    pushd conda-build
    $prefix/bin/pip install .
    popd

    git clone https://github.com/conda/conda_build_test_recipe.git

    $prefix/bin/conda info
}


usr_local_install() {
    sudo -E -u root bash -c "source utils/functions.sh && install_conda_dev /usr/local"
    export INSTALL_PREFIX="/usr/local"
    export PATH=$INSTALL_PREFIX/bin:$PATH
    sudo -E -u root chown -R root:root ./conda
    ls -al ./conda
}

