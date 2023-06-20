#!/usr/bin/env bash

set -o errtrace -o pipefail -o errexit

TEST_SPLITS="${TEST_SPLITS:-1}"
TEST_GROUP="${TEST_GROUP:-1}"

eval "$(sudo python -m conda init bash --dev)"
conda-build \
    tests/test-recipes/activate_deactivate_package \
    tests/test-recipes/pre_link_messages_package
conda info

python -m pytest \
    --cov=conda \
    --store-durations \
    --durations-path=./tools/durations/${OS}.json \
    --splitting-algorithm=least_duration \
    -v \
    --splits=${TEST_SPLITS} \
    --group=${TEST_GROUP}
