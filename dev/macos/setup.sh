#!/bin/bash
set -ex

# restoring the default for changeps1 to have parity with dev
conda config --set changeps1 true
# install all test requirements
conda install --yes --solver=libmamba --name conda-test-env --file tests/requirements.txt --file tests/requirements-extra.txt
conda update --yes openssl ca-certificates certifi
