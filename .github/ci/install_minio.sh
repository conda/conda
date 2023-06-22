#!/usr/bin/env bash

# Download MinIO
MINIOARCH="${TARGETARCH:-$(uname -m)}"

ARCH="$(uname -m)"
case "${ARCH}" in
    aarch64) ARCH=arm64;;
    x86_64) ARCH=amd64;;
    ppc64el) ARCH=ppc64le;;
    *) ARCH=$1;
esac
curl -sL -o minio "https://dl.minio.io/server/minio/release/$(uname -s)-${ARCH}/${MINIO_RELEASE:-minio}"

# Install MinIO
chmod +x minio
cp minio $CONDA_PREFIX/bin/minio
