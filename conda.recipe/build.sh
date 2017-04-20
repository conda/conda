# necessary because conda symlinks
unlink $PREFIX/bin/conda || true
unlink $PREFIX/bin/activate || true
unlink $PREFIX/bin/deactivate || true

$PYTHON conda.recipe/setup.py install

. utils/functions.sh

install_conda_shell_scripts $PREFIX
