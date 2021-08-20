#!/usr/bin/env bash

set -o errtrace -o pipefail -o errexit

conda info
pytest -m "not integration" -v --splits ${TEST_SPLITS} --group=${TEST_GROUP}
