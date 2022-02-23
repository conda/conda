#!/usr/bin/env bash

echo "Initializing conda in dev mode..."
eval "$(sudo /opt/conda/bin/python -m conda init --dev bash)"
echo "Factory config is:"
grep -e "conda location" -e "conda version" -e "python version" <(conda info -a) | sed 's/^\s*/  /'
if [[ $RUNNING_ON_DEVCONTAINER == 1 ]]; then
    conda init
fi
echo "Done! Now running:"
grep -e "conda location" -e "conda version" -e "python version" <(conda info -a) | sed 's/^\s*/  /'
