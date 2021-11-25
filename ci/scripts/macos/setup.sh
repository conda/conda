#!/usr/bin/env bash

set -o errtrace -o pipefail -o errexit

echo "Initializing conda in dev mode..."
echo "Factory config is:"
grep -e "conda location" -e "conda version" -e "python version" <(conda info -a) | sed 's/^\s*/  /'
conda install -yq pip conda-build conda-verify pytest
conda update openssl ca-certificates certifi
eval "$(python -m conda init bash --dev)"
echo "Done! Now running:"
grep -e "conda location" -e "conda version" -e "python version" <(conda info -a) | sed 's/^\s*/  /'
