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

install_python() {
    INSTALL_PREFIX=${1:-~/miniconda}

    # strategy is to use Miniconda to install python, but then remove all vestiges of conda
    curl -sSL $MINICONDA_URL -o ~/miniconda.sh
    chmod +x ~/miniconda.sh
    mkdir -p $INSTALL_PREFIX
    ~/miniconda.sh -bfp $INSTALL_PREFIX
    hash -r
    $INSTALL_PREFIX/bin/conda install -y -q python=$PYTHON_VERSION
    local site_packages=$($INSTALL_PREFIX/bin/python -c "from distutils.sysconfig import get_python_lib as g; print(g())")
    rm -rf $INSTALL_PREFIX/bin/activate \
       $INSTALL_PREFIX/bin/conda \
       $INSTALL_PREFIX/bin/conda-env \
       $INSTALL_PREFIX/bin/deactivate \
       $INSTALL_PREFIX/conda-meta/conda-*.json \
       $INSTALL_PREFIX/conda-meta/requests-*.json \
       $INSTALL_PREFIX/conda-meta/pyopenssl-*.json \
       $INSTALL_PREFIX/conda-meta/cryptography-*.json \
       $INSTALL_PREFIX/conda-meta/idna-*.json \
       $INSTALL_PREFIX/conda-meta/ruamel-*.json \
       $INSTALL_PREFIX/conda-meta/pycrypto-*.json \
       $INSTALL_PREFIX/conda-meta/pycosat-*.json \
       $site_packages/conda* \
       $site_packages/requests* \
       $site_packages/pyopenssl* \
       $site_packages/cryptography* \
       $site_packages/idna* \
       $site_packages/ruamel* \
       $site_packages/pycrypto* \
       $site_packages/pycosat*
    hash -r
    which -a python
    $INSTALL_PREFIX/bin/python --version
    $INSTALL_PREFIX/bin/pip --version

}


install_conda_dev() {

    INSTALL_PREFIX=${1:-~/miniconda}

    curl -sSL $MINICONDA_URL -o ~/miniconda.sh
    chmod +x ~/miniconda.sh
    mkdir -p $INSTALL_PREFIX
    ~/miniconda.sh -bfp $INSTALL_PREFIX
    hash -r
    $INSTALL_PREFIX/bin/conda install -y -q python=$PYTHON_VERSION
    local site_packages=$($INSTALL_PREFIX/bin/python -c "from distutils.sysconfig import get_python_lib as g; print(g())")
    rm -rf $INSTALL_PREFIX/bin/activate \
       $INSTALL_PREFIX/bin/conda \
       $INSTALL_PREFIX/bin/conda-env \
       $INSTALL_PREFIX/bin/deactivate \
       $INSTALL_PREFIX/conda-meta/conda-*.json \
       $INSTALL_PREFIX/conda-meta/requests-*.json \
       $INSTALL_PREFIX/conda-meta/pyopenssl-*.json \
       $INSTALL_PREFIX/conda-meta/cryptography-*.json \
       $INSTALL_PREFIX/conda-meta/idna-*.json \
       $INSTALL_PREFIX/conda-meta/ruamel-*.json \
       $INSTALL_PREFIX/conda-meta/pycrypto-*.json \
       $INSTALL_PREFIX/conda-meta/pycosat-*.json \
       $site_packages/conda* \
       $site_packages/requests* \
       $site_packages/pyopenssl* \
       $site_packages/cryptography* \
       $site_packages/idna* \
       $site_packages/ruamel* \
       $site_packages/pycrypto* \
       $site_packages/pycosat*
    hash -r
    $INSTALL_PREFIX/bin/pip install -r utils/requirements-test.txt
    $INSTALL_PREFIX/bin/python utils/setup-testing.py develop
}
