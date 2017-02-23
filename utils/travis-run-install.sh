set -e
set -x

export INSTALL_PREFIX=~/miniconda
export PATH=$INSTALL_PREFIX/bin:$PATH
source utils/functions.sh

osx_setup() {
    # brew update || brew update
    # brew outdated openssl || brew upgrade openssl
    brew install zsh

    # rvm get head

    install_conda_dev
}


linux_setup() {
    if [[ $FLAKE8 == true ]]; then
        pip install flake8
    elif [[ $TRAVIS_SUDO == true ]]; then
        usr_local_install
    elif [[ -n $CONDA_BUILD ]]; then
        install_conda_build
    else
        install_conda_dev
    fi
}


case "$(uname -s)" in
    'Darwin')
        osx_setup
        ;;
    'Linux')
        linux_setup
        ;;
    *)  ;;
esac

set +x
