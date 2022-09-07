#!/bin/bash

echo $PKG_VERSION > conda/.version
$PYTHON setup.py install --single-version-externally-managed --record record.txt
if [[ ! $(uname) =~ MINGW* ]]; then
  rm -rf "$SP_DIR/conda/shell/*.exe"
fi
$PYTHON -m conda init --install
if [[ $(uname) =~ MINGW* ]]; then
  sed -i "s|CONDA_EXE=.*|CONDA_EXE=\'${PREFIXW//\\/\\\\}\\\\Scripts\\\\conda.exe\'|g" $PREFIX/etc/profile.d/conda.sh
fi
