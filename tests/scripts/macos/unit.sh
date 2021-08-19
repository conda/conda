#!/usr/bin/env bash

set -o errtrace -o pipefail -o errexit

TEST_SPLITS="${TEST_SPLITS:-1}"
TEST_GROUP="${TEST_GROUP:-1}"

conda info
pytest -m "not integration" -vv --splits ${TEST_SPLITS} --group=${TEST_GROUP}
