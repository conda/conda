#!/usr/bin/env bash

set -o errtrace -o pipefail -o errexit

apt-get update --fix-missing
apt-get install -y --no-install-recommends \
    tini wget curl build-essential bzip2 ca-certificates \
    libglib2.0-0 libxext6 libsm6 libxrender1 git mercurial subversion \
    sudo htop less nano man grep
apt-get clean
rm -rf /var/lib/apt/lists/*

useradd -m -s /bin/bash test_user
usermod -u 1001 test_user
groupmod -g 1001 test_user
echo "test_user ALL=(ALL) NOPASSWD:ALL" >> /etc/sudoers

### Gitpod user ###
useradd -l -u 33333 -G sudo -md /home/gitpod -s /bin/bash -p gitpod gitpod
echo "gitpod ALL=(ALL) NOPASSWD:ALL" >> /etc/sudoers

### Prevent git safety errors when mounting directories ###
git config --global --add safe.directory /opt/conda-src
