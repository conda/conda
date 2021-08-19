#!/usr/bin/env bash

set -o errtrace -o pipefail -o errexit

conda-build tests/test-recipes/activate_deactivate_package
pytest -m "integration" -v
python -m conda.common.io
