#!/bin/sh
set -uo pipefail

# Invoke with:
#   $ bash ./tests/integration/proxy/proxy-test.sh
#
# NOTES:
#   * PWD should be the conda project root
#   * docker is required, and executable without sudo
#   * squidusers file has condauser:condapass for credentials
#   * to look at logs for squid proxy, use:
#       $ cat ./tests/integration/proxy/squid_log/*
#
# REFERENCES:
#   https://veesp.com/en/blog/squid-authentication
#   https://wiki.squid-cache.org/Features/Authentication


SRC_DIR="$PWD"

[ -f "$SRC_DIR/conda/__main__.py" ] && [ -f "$SRC_DIR/setup.py" ] || (echo "Current working directory must be conda project root." && exit 1)
which docker > /dev/null || (echo "docker required but not found" && exit 1)
docker --version > /dev/null || (echo "Cannot execute docker. Apparently needs sudo?" && exit 1)


rm -rf "$SRC_DIR"/tests/integration/proxy/squid_log/*
CID=$(docker run \
    --detach \
    --rm \
    -v $SRC_DIR/tests/integration/proxy/squid.conf:/etc/squid/squid.conf:ro \
    -v $SRC_DIR/tests/integration/proxy/squidusers:/etc/squid/squidusers:ro \
    -v $SRC_DIR/tests/integration/proxy/squid_log:/var/log/squid:rw \
    -p 3128:3128 \
    kalefranz/squid)

echo "waiting for proxy to start"
( tail -f -n0 "$SRC_DIR/tests/integration/proxy/squid_log/cache.log" & ) | grep -q "Accepting HTTP Socket connections at"


_fail() {
  echo -e "$1"
  echo "removing container $CID"
  docker rm --force $CID > /dev/null
  exit 1
}


# Don't use repodata Cache-Control
export CONDA_LOCAL_REPODATA_TTL=0

# Ensure we have an empty package cache
export CONDA_PKGS_DIRS="$SRC_DIR/tests/integration/proxy/temp"
mkdir -p "$CONDA_PKGS_DIRS" || _fail "permissions error"
touch "$CONDA_PKGS_DIRS/permissions-check" || _fail "permissions error"
rm -rf "$CONDA_PKGS_DIRS"/*


# ###########################################################
# Test that we have failures when directing traffic through proxy with wrong password
# ###########################################################
export CONDARC="$SRC_DIR/tests/integration/proxy/condarc.proxybad"

# test for repodata failure
echo "test expecting repodata failure"
captured="$(conda search zlib 2>&1)"
rc=$?
[ $rc -eq 1 ] || _fail "'conda search zlib' was expected to fail\n$captured"
rm -rf "$CONDA_PKGS_DIRS"/*

# test for package download failure
echo "test expecting package download failure"
captured="$(conda install --mkdir -y -q -p $CONDA_PKGS_DIRS/test-env https://repo.continuum.io/pkgs/main/osx-64/six-1.11.0-py36h0e22d5e_1.tar.bz2 2>&1)"
rc=$?
[ $rc -eq 1 ] || _fail "'conda install' was expected to fail\n$captured"
rm -rf "$CONDA_PKGS_DIRS"/*


# ###########################################################
# Test that directing traffic through proxy with correct password succeeds
# ###########################################################
export CONDARC="$SRC_DIR/tests/integration/proxy/condarc.proxygood"

# test for repodata success
echo "test expecting repodata success"
captured="$(conda search zlib 2>&1)"
rc=$?
[ $rc -eq 0 ] || _fail "'conda search zlib' was expected to succeed\n$captured"
echo "$captured" | grep -q 1.2.11 || _fail "'conda search zlib' was expected to contain zlib version 1.2.11"\n$captured
rm -rf "$CONDA_PKGS_DIRS"/*

# test for package download success
echo "test expecting package download success"
captured="$(conda install --mkdir -y -q -p $CONDA_PKGS_DIRS/test-env https://repo.continuum.io/pkgs/main/osx-64/six-1.11.0-py36h0e22d5e_1.tar.bz2 2>&1)"
rc=$?
[ $rc -eq 0 ] || _fail "'conda install' was expected to succeed\n$captured"
[ -f "$CONDA_PKGS_DIRS/test-env/conda-meta/history" ] || _fail "history file expected\n$captured"
[ -f "$CONDA_PKGS_DIRS/test-env/lib/python3.6/site-packages/six.py" ] || _fail "six.py file expected\n$captured"
rm -rf "$CONDA_PKGS_DIRS"/*


# ###########################################################
# clean up
# ###########################################################

echo "removing container $CID"
docker rm --force $CID > /dev/null

echo
echo ">>>>> ALL TESTS COMPLETED <<<<<"
echo
