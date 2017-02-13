set -e
set -x

export PATH="~/miniconda/bin:$PATH"


osx_setup() {
    brew update || brew update

    brew outdated openssl || brew upgrade openssl
    brew install zsh

#    # install pyenv
#    git clone https://github.com/yyuu/pyenv.git ~/.pyenv
#    PYENV_ROOT="$HOME/.pyenv"
#    PATH="$PYENV_ROOT/bin:$PATH"
#    eval "$(pyenv init -)"
#
#    case "$PYTHON_VERSION" in
#        '2.7')
#            curl -O https://bootstrap.pypa.io/get-pip.py
#            python get-pip.py --user
#            ;;
#        '3.4')
#            pyenv install 3.4.5
#            pyenv global 3.4.5
#            ;;
#        '3.5')
#            pyenv install 3.5.2
#            pyenv global 3.5.2
#            ;;
#        '3.6')
#            pyenv install 3.6.0
#            pyenv global 3.6.0
#            ;;
#    esac
#    pyenv rehash
#    export PYTHON_EXE="$(pyenv which python)"

    rvm get head
}


install_python() {
    # strategy is to use Miniconda to install python, but then remove all vestiges of conda
   curl -sSL $MINICONDA_URL -o ~/miniconda.sh
   chmod +x ~/miniconda.sh
   ~/miniconda.sh -bfp ~/miniconda
   hash -r
   conda install -y -q python=$PYTHON_VERSION
   local site_packages=$(~/miniconda/bin/python -c "from distutils.sysconfig import get_python_lib as g; print(g())")
   rm -rf ~/miniconda/bin/activate \
       ~/miniconda/bin/conda \
       ~/miniconda/bin/deactivate \
       ~/miniconda/conda-meta/conda-*.json \
       ~/miniconda/conda-meta/requests-*.json \
       ~/miniconda/conda-meta/pyopenssl-*.json \
       ~/miniconda/conda-meta/cryptography-*.json \
       ~/miniconda/conda-meta/idna-*.json \
       ~/miniconda/conda-meta/ruamel-*.json \
       ~/miniconda/conda-meta/pycrypto-*.json \
       ~/miniconda/conda-meta/pycosat-*.json \
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
   python --version
   pip --version

}

miniconda_install() {
    curl -L https://repo.continuum.io/miniconda/Miniconda3-4.0.5-Linux-x86_64.sh -o ~/miniconda.sh
    bash ~/miniconda.sh -bfp ~/miniconda
    export PATH=~/miniconda/bin:$PATH
    hash -r
    which -a conda
    conda install -y -q pip conda 'python>=3.6'
    conda info
    which -a pip
    which -a python
    conda config --set auto_update_conda false
}


conda_build_install() {
    # install conda
    rm -rf $(~/miniconda/bin/python -c "import site; print(site.getsitepackages()[0])")/conda
    ~/miniconda/bin/python utils/setup-testing.py install
    hash -r
    conda info

    # install conda-build test dependencies
    conda install -y -q pytest pytest-cov pytest-timeout mock
    conda install -y -q -c conda-forge perl pytest-xdist
    conda install -y -q anaconda-client numpy

    ~/miniconda/bin/python -m pip install pytest-catchlog pytest-mock

    conda config --set add_pip_as_python_dependency true

    # install conda-build runtime dependencies
    conda install -y -q filelock jinja2 patchelf conda-verify setuptools contextlib2 pkginfo

    # install conda-build
    git clone -b $CONDA_BUILD --single-branch --depth 1000 https://github.com/conda/conda-build.git
    rm -rf $(~/miniconda/bin/python -c "import site; print(site.getsitepackages()[0])")/conda_build
    pushd conda-build
    ~/miniconda/bin/pip install .
    hash -r
    conda info
    popd

    git clone https://github.com/conda/conda_build_test_recipe.git
}


# Set global variables for this script
case "$(uname -s)" in
    'Darwin')
        MINICONDA_URL="https://repo.continuum.io/miniconda/Miniconda3-4.2.12-MacOSX-x86_64.sh"
        osx_setup
        ;;
    'Linux')
        MINICONDA_URL="https://repo.continuum.io/miniconda/Miniconda3-4.2.12-Linux-x86_64.sh"
        ;;
    *)  ;;
esac


if [[ $FLAKE8 == true ]]; then
    install_python
    pip install flake8
elif [[ -n $CONDA_BUILD ]]; then
    miniconda_install
    conda_build_install
else
    install_python
    pip install -r utils/requirements-test.txt
fi
