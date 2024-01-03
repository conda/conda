#!/usr/bin/env bash

set -o errtrace -o pipefail -o errexit

pushd $TEMP
cd \conda_src
.\dev-init.bat
conda info

# installing the needed pytest plugin for codspeed.io
pip install pytest-codspeed
python -m pytest -m "benchmark" --codspeed || goto :error
