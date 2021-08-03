#!/usr/bin/env bash

set -o errtrace -o pipefail -o errexit

pip install -r docs/requirements.txt
cd docs
make html
