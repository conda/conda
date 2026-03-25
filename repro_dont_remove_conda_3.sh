#!/usr/bin/env bash
set -euo pipefail

# Create broken conda, in a way that also happens when pip installs
# a conda dependency.

PYTHON_BIN="${PYTHON_BIN:-python}"
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

PREFIX="${PREFIX:-$(mktemp -d "${TMPDIR:-/tmp/}conda-removeerror.XXXXXX")}"
PKGS_DIR="${PKGS_DIR:-$(mktemp -d "${TMPDIR:-/tmp/}conda-removeerror-pkgs.XXXXXX")}"

echo "Using repo root: ${REPO_ROOT}"
echo "Using prefix: ${PREFIX}"
echo "Using package cache: ${PKGS_DIR}"

export CONDA_PKGS_DIRS="${PKGS_DIR}"
export PIP_BREAK_SYSTEM_PACKAGES=1
export PIP_NO_BUILD_ISOLATION=1
export CONDA_PREFIX="${PREFIX}"

# This isn't quiet?
"${PYTHON_BIN}" -m conda create --prefix="${PREFIX}" pip conda python=3.12 --yes --quiet

# Simulate a dependency checked by RemoveError being installed or upgraded with pip.
shopt -s nullglob
meta_files=("${PREFIX}"/conda-meta/conda-package-handling-*.json)
if ((${#meta_files[@]} > 0)); then
  rm -f "${meta_files[0]}"
else
  echo "No conda-package-handling record found in ${PREFIX}/conda-meta"
fi
shopt -u nullglob

export CONDA_ROOT_PREFIX="${PREFIX}"
export CONDA_PREFIX="${PREFIX}"

# This may fail depending on solver/package state; no assertions.
set +e
"${PREFIX}/bin/conda" install --prefix="${PREFIX}" --yes --quiet setuptools-scm
install_exit=$?
set -e

set +e
"${PREFIX}/bin/conda" uninstall --prefix="${PREFIX}" --yes --quiet setuptools-scm
uninstall_exit=$?
set -e

echo "Final install exit code: ${install_exit}"
echo "Final uninstall exit code: ${uninstall_exit}"
