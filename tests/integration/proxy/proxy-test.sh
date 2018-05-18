#!/bin/sh
set -euxo pipefail

# Invoke with:
#   $ bash ./tests/integration/proxy/proxy-test.sh
#
# NOTE: PWD should be the conda project root
#
# To look at logs for squid proxy, use:
#   $ cat ./tests/integration/proxy/squid_logs/*

# squidusers file has condauser:condapass for credentials

# REFERENCES:
#   https://veesp.com/en/blog/squid-authentication
#   https://wiki.squid-cache.org/Features/Authentication


SRC_DIR="$PWD"

[ -f "$SRC_DIR/conda/__main__.py" ] && [ -f "$SRC_DIR/tests/conftest.py" ] || (echo "Current working directory must be conda project root." && exit 1)

which docker > /dev/null || (echo "docker required but not found" && exit 1)
docker --version > /dev/null || (echo "Cannot execute docker. Apparently needs sudo?" && exit 1)

docker run \
    -v $SRC_DIR/tests/integration/proxy/squid.conf:/etc/squid/squid.conf:ro \
    -v $SRC_DIR/tests/integration/proxy/squidusers:/etc/squid/squidusers:ro \
    -v $SRC_DIR/tests/integration/proxy/squid_log:/var/log/squid:rw \
    -p 3128:3128 \
    kalefranz/squid


# Ensure we make a web request for each required repodata.json
export CONDA_LOCAL_REPODATA_TTL=0

# Ensure we have an empty package cache
export CONDA_PKGS_DIRS="$SRC_DIR/tests/integration/proxy/temp"
mkdir -p "$CONDA_PKGS_DIRS"
touch "$CONDA_PKGS_DIRS/permissions-check"
rm -rf "$CONDA_PKGS_DIRS/*"

# ###########################################################
# Test that we have failures when directing traffic through proxy with wrong password
# ###########################################################
export CONDARC="$SRC_DIR/tests/integration/proxy/condarc.proxybad"

# test for repodata failure
captured="$(conda search zlib 2>&1)"
rc=$?
[ $rc -eq 1 ] || (echo "'conda search zlib' was expected to fail" && exit 1)
rm -rf "$CONDA_PKGS_DIRS/*"

# test for package download failure
captured="$(conda install --mkdir -y -q -p \"$CONDA_PKGS_DIRS/test-env\" https://repo.continuum.io/pkgs/main/osx-64/six-1.11.0-py36h0e22d5e_1.tar.bz2 2>&1)"
rc=$?
[ $rc -eq 1 ] || (echo "'conda install' was expected to fail" && exit 1)
rm -rf "$CONDA_PKGS_DIRS/*"


# ###########################################################
# Test that directing traffic through proxy with correct password succeeds
# ###########################################################
export CONDARC="$SRC_DIR/tests/integration/proxy/condarc.proxygood"

# test for repodata success
captured="$(conda search zlib 2>&1)"
rc=$?
[ $rc -eq 0 ] || (echo "'conda search zlib' was expected to succeed" && exit 1)
echo "$captured" | grep -q 1.2.11 || (echo "'conda search zlib' was expected to contain zlib version 1.2.11" && exit 1)
rm -rf "$CONDA_PKGS_DIRS/*"

# test for package download success
captured="$(conda install --mkdir -y -q -p \"$CONDA_PKGS_DIRS/test-env\" https://repo.continuum.io/pkgs/main/osx-64/six-1.11.0-py36h0e22d5e_1.tar.bz2 2>&1)"
rc=$?
[ $rc -eq 0 ] || (echo "'conda install' was expected to succeed" && exit 1)
[ -f "$CONDA_PKGS_DIRS/test-env/conda-meta/history" ] || (echo "history file expected" && exit 1)
[ -f "$CONDA_PKGS_DIRS/test-env/lib/python3.6/site-packages/six.py" ] || (echo "six.py file expected" && exit 1)
rm -rf "$CONDA_PKGS_DIRS/*"


# TODO: shut down docker container
