#!/usr/bin/env bash

set -o errtrace -o pipefail -o errexit

TEST_SPLITS="${TEST_SPLITS:-1}"
TEST_GROUP="${TEST_GROUP:-1}"

# TODO: once #11865 is merged this can be updated
eval "$(sudo python -m conda init bash --dev)"
conda info
conda clean -ayq

pytest -m "not integration" -v --splits ${TEST_SPLITS} --group=${TEST_GROUP}
