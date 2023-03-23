#!/bin/bash
set -ex

# Download the Minio server, needed for S3 tests
if [[ ! -f minio ]]
then
    curl -sL -o minio https://dl.min.io/server/minio/release/darwin-amd64/archive/minio.RELEASE.2023-03-13T19-46-17Z
fi
chmod +x minio
sudo cp minio /usr/local/bin/minio

# restoring the default for changeps1 to have parity with dev
conda config --set changeps1 true
# install all test requirements
conda install --yes --name conda-test-env --file tests/requirements.txt
conda update --yes openssl ca-certificates certifi
