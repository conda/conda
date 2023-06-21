#!/usr/bin/env bash

set -o errtrace -o pipefail -o errexit

apt-get update --fix-missing
apt-get install -y --no-install-recommends \
    tini wget curl build-essential bzip2 ca-certificates \
    libglib2.0-0 libxext6 libsm6 libxrender1 git mercurial subversion \
    sudo htop less nano man grep
apt-get clean
rm -rf /var/lib/apt/lists/*

# Download the Minio server, needed for S3 tests
minioarch="${TARGETARCH:-$(uname -m)}"
if [ "${minioarch}" = "aarch64" ]; then
    minioarch=arm64
elif [ "${minioarch}" = "x86_64" ]; then
    minioarch=amd64
elif [ "${minioarch}" = "ppc64el" ]; then
    minioarch=ppc64le
fi
minio_release="${MINIO_RELEASE:-minio}" # use 'archive/XXXX' for older releases
curl -sL -o minio "https://dl.minio.io/server/minio/release/linux-${minioarch}/${minio_release}"
chmod +x minio
sudo mv minio /usr/local/bin/minio

useradd -m -s /bin/bash test_user
usermod -u 1001 test_user
groupmod -g 1001 test_user
echo "test_user ALL=(ALL) NOPASSWD:ALL" >> /etc/sudoers

### Gitpod user ###
useradd -l -u 33333 -G sudo -md /home/gitpod -s /bin/bash -p gitpod gitpod
echo "gitpod ALL=(ALL) NOPASSWD:ALL" >> /etc/sudoers

### Prevent git safety errors when mounting directories ###
git config --global --add safe.directory /opt/conda-src
