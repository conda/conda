unlink $PREFIX/bin/conda
CONDA_DEFAULT_ENV='' $PYTHON setup.py install
CONDA_DEFAULT_ENV='' python setup.py --version > __conda_version__.txt
