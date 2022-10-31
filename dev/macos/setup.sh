#!/bin/bash
set -ex

# Download the Minio server, needed for S3 tests
if [[ ! -f minio ]]
then
    curl -LO https://dl.minio.io/server/minio/release/darwin-amd64/minio
fi
chmod +x minio
sudo cp minio /usr/local/bin/minio

# restoring the default for changeps1 to have parity with dev
conda config --set changeps1 true
# make sure the caching works correctly
conda config --set use_only_tar_bz2 true
# install all test requirements
conda install --name conda-test-env --yes --file tests/requirements.txt
conda update openssl ca-certificates certifi
