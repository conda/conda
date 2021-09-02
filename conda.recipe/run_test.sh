#!/usr/bin/env bash
set -x

unset CONDA_SHLVL
unset _CE_CONDA
unset _CE_M
unset CONDA_EXE
eval "$(python -m conda shell.bash hook)"
conda activate base
export PYTHON_MAJOR_VERSION=$(python -c "import sys; print(sys.version_info[0])")
export TEST_PLATFORM=$(python -c "import sys; print('win' if sys.platform.startswith('win') else 'unix')")
export PYTHONHASHSEED=$(python -c "import random as r; print(r.randint(0,4294967296))") && echo "PYTHONHASHSEED=$PYTHONHASHSEED"
env | sort
conda info
conda create -y -p ./built-conda-test-env python=3.9
conda activate ./built-conda-test-env
echo $CONDA_PREFIX
[ "$CONDA_PREFIX" = "$PWD/built-conda-test-env" ] || exit 1
[ $(python -c "import sys; print(sys.version_info[1])") = 9 ] || exit 1
python -c '__requires__ = ["ruamel_yaml_conda >= 0.11.14"]; import pkg_resources' || exit 1
conda deactivate
pytest tests -m "not integration and not installed" -vv
