#!/usr/bin/env bash
# Copyright (C) conda contributors
# SPDX-License-Identifier: BSD-3-Clause
# Needs conda-lockfiles in base. Run from repo root:
#   bash tests/generate_locks_by_python.sh [path/to/environment.yml]
#
# For each of 3.10–3.14, copies the YAML with sed rewriting any dependency line
# "- python ..." to "- python X.Y.*", then env create + export.
#
# Uses $CONDA_EXE when set (parent install after activate), else $(conda info --base)/bin/conda;
# base/prefix come from that binary so a nested conda-in-env does not miss conda-lockfiles in outer base.
set -euo pipefail
cd "$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
if [[ -n "${CONDA_EXE:-}" && -x "$CONDA_EXE" ]]; then
  conda="$CONDA_EXE"
else
  _b="$(conda info --base)"
  conda="${_b}/bin/conda"
fi
base="$("$conda" info --base)"
env=_conda_lock_by_py
prefix="${base}/envs/$env"
file="${1:-tests/environment.yml}"

for py in 3.10 3.11 3.12 3.13; do
  tmp=$(mktemp)
  sed -E 's/^([[:space:]]*-[[:space:]]*)python.*/\1python '"${py}"'.\*/' "$file" >"$tmp"
  tag="${py//./}"
  out="tests/conda-lock-python${tag}.yml"
  echo "==> python ${py} -> ${out}" >&2

  "$conda" remove -p "$prefix" --all -y 2>/dev/null || true
  "$conda" create -p "$prefix" --file "$tmp" -y
  rm -f "$tmp"

  "$conda" export -vv -p "$prefix" --format conda-lock-v1 --file "$out" \
    --platform win-64 --platform linux-64 --platform osx-arm64 --platform osx-64 --platform linux-aarch64
done
