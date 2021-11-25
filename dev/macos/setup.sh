#!/usr/bin/env bash

set -o errtrace -o pipefail -o errexit

# restoring the default for changeps1 to have parity with dev
conda config --set changeps1 true

echo "Initializing conda in dev mode..."
echo "Factory config is:"
grep -e "conda location" -e "conda version" -e "python version" <(conda info -a) | sed 's/^\s*/  /'
conda install --name conda-test-env --yes --file tests/requirements.txt
conda update openssl ca-certificates certifi
eval "$(sudo python -m conda init bash --dev)"
echo "Done! Now running:"
grep -e "conda location" -e "conda version" -e "python version" <(conda info -a) | sed 's/^\s*/  /'
