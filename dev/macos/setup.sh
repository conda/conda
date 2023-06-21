#!/bin/bash
set -ex

# Download the Minio server, needed for S3 tests
if [[ ! -f minio ]]; then
    minio_release="${MINIO_RELEASE:-minio}" # use 'archive/XXXX' for older releases
    curl -sL -o minio "https://dl.min.io/server/minio/release/darwin-amd64/${minio_release}"
fi
chmod +x minio
sudo cp minio /usr/local/bin/minio
