#!/usr/bin/env bash

set -o errtrace -o pipefail -o errexit

conda info
pytest -m "not integration" -v
