#!/bin/bash
set -ex

# Download the Minio server, needed for S3 tests
if [[ ! -f minio ]]
then
    minio_release="${MINIO_RELEASE:-minio}" # use 'archive/XXXX' for older releases
    curl -sL -o minio "https://dl.min.io/server/minio/release/darwin-amd64/${minio_release}"
fi
chmod +x minio
sudo cp minio /usr/local/bin/minio

# restoring the default for changeps1 to have parity with dev
conda config --set changeps1 true
# install all test requirements
conda install --yes --name conda-test-env --file tests/requirements.txt
