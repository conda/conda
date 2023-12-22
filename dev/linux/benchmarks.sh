#!/usr/bin/env bash

set -o errtrace -o pipefail -o errexit

### Prevent git safety errors when mounting directories ###
git config --global --add safe.directory /opt/conda-src

# make sure all test requirements are installed
sudo /opt/conda/bin/conda install --quiet -y --file tests/requirements.txt "conda-forge::menuinst>=2" --repodata-fn=repodata.json
eval "$(sudo /opt/conda/bin/python -m conda init --dev bash)"
# installing the needed pytest plugin for codspeed.io
pip install pytest-codspeed
conda info
# remove the pkg cache.  We can't hardlink from here anyway.  Having it around causes log problems.
sudo rm -rf /opt/conda/pkgs/*-*-*
# put temporary files on same filesystem
export TMP=$HOME/pytesttmp
mkdir -p $TMP
python -m pytest \
    --basetemp=$TMP \
    -m "benchmark" \
    --codspeed
