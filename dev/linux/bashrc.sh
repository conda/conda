#!/usr/bin/env bash

print_conda_info() {
    grep -e "conda location" -e "conda version" -e "python version" -e "sys.version" <(conda info -a) | sed 's/^\s*/  /'
    conda config --show channels | sed 's/^\s*/  /'
}

echo "Initializing conda in dev mode..."

### Prevent git safety errors when mounting directories ###
git config --global --add safe.directory /opt/conda-src

echo "Factory config is:"
print_conda_info
eval "$(sudo /opt/conda/bin/python -m conda init --dev bash)"
if [[ $RUNNING_ON_DEVCONTAINER == 1 ]]; then
    conda init
fi
echo "Done! Now running:"
print_conda_info
