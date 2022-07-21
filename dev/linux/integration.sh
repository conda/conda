#!/usr/bin/env bash

set -o errtrace -o pipefail -o errexit

TEST_SPLITS="${TEST_SPLITS:-1}"
TEST_GROUP="${TEST_GROUP:-1}"

## TODO: REMOVE; TEMPORARY BEFORE MERGE
# Download the Minio server, needed for S3 tests
curl -LO https://dl.minio.io/server/minio/release/linux-amd64/minio
chmod +x minio
sudo mv minio /usr/bin/minio
conda install -yq conda-forge::pytest-xprocess boto3
## /TODO

eval "$(sudo /opt/conda/bin/python -m conda init --dev bash)"
sudo su root -c "/opt/conda/bin/conda install -yq conda-build"
conda-build tests/test-recipes/activate_deactivate_package tests/test-recipes/pre_link_messages_package
conda info
pytest -m "integration" -v --splits ${TEST_SPLITS} --group=${TEST_GROUP}
python -m conda.common.io
