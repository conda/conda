set -e
set -x


flake8_install() {
    pip install flake8
}


main_install() {
    pip install psutil ruamel.yaml pycosat pycrypto
    case $TRAVIS_PYTHON in
      '2.7')
          pip install enum34 futures
          ;;
      *) ;;
    esac
}


test_install() {
    pip install mock pytest pytest-cov pytest-timeout radon responses
}


if [[ $FLAKE8 == true ]]; then
    main_install
    flake8_install
else
    main_install
    test_install
fi
