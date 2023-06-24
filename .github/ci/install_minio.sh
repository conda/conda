#!/usr/bin/env bash

# Check if MinIO was previously downloaded
if [[ -f minio ]]; then
    echo "MinIO already downloaded."
else
    echo "Downloading MinIO."
    ARCH="${TARGETARCH:-$(uname -m)}"
    case "${ARCH}" in
        aarch64) ARCH=arm64;;
        x86_64) ARCH=amd64;;
        ppc64el) ARCH=ppc64le;;
    esac
    OS=$(uname -s | tr "[:upper:]" "[:lower:]")
    curl -sL -o minio "https://dl.min.io/server/minio/release/${OS}-${ARCH}/${MINIO_RELEASE:-minio}"
fi

# Install MinIO
echo "Installing MinIO."
chmod +x minio
cp minio ${CONDA_PREFIX}/bin/minio
