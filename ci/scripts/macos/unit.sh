#!/usr/bin/env bash

set -o errtrace -o pipefail -o errexit

eval "$(sudo ./devenv/bin/python -m conda init --dev bash)"
conda info
pytest -m "not integration" -v
