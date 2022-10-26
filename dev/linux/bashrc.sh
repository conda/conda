#!/usr/bin/env bash

echo "Initializing conda in dev mode..."
echo "Factory config is:"
grep -e "conda location" -e "conda version" -e "python version" <(conda info -a) | sed 's/^\s*/  /'

# TODO: once #11865 is merged this can be updated
eval "$(sudo /opt/conda/bin/python -m conda init --dev bash)"
if [[ $RUNNING_ON_DEVCONTAINER == 1 ]]; then
    conda init
fi
echo "Done! Now running:"
grep -e "conda location" -e "conda version" -e "python version" <(conda info -a) | sed 's/^\s*/  /'
