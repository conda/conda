# . utils/functions.sh && install_conda_full
$PYTHON setup.py install
$PYTHON -c "from conda.core.initialize import install; install('$PREFIX')"


