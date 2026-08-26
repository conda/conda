#!/usr/bin/env bash
# build-freethreaded-deps.sh
#
# Builds cp314t (freethreaded Python 3.14) conda packages for the blockers
# that are missing cp314t builds on conda-forge:
#
#   pycosat, menuinst, libmambapy, conda-pypi, xonsh (Linux/macOS),
#   pywin32 (Windows)
#
# It also builds `conda` itself (from this local checkout) as a cp314t
# package, so the whole stack -- conda plus its freethreaded-only
# dependencies -- can be installed and tested together.
#
# The built packages are placed in <repo-root>/freethreaded-packages/ and
# indexed as a local conda channel, ready for use with:
#
#   conda install --channel "file://$PWD/freethreaded-packages" ...
#
# Usage:
#   ./build-freethreaded-deps.sh [--output-dir <dir>] [--clean] [--upload]
#                                 [--user <anaconda.org user>] [--label <label>]
#
#   --output-dir <dir>  Where to write built packages (default: freethreaded-packages/)
#   --clean             Remove the output directory before building
#   --upload            After building, upload all packages to anaconda.org via
#                        upload-freethreaded-packages.sh (requires anaconda-client
#                        to already be logged in, or ANACONDA_API_TOKEN to be set)
#   --user <user>        anaconda.org user/org to upload to (default: whoami from anaconda-client)
#   --label <label>      anaconda.org label to upload to (default: cp314t)
#
# Requirements:
#   - conda (with conda-forge channel, e.g. miniforge)
#   - rattler-build  (installed automatically via pixi if missing)
#   - anaconda-client (only required when using --upload)

set -euo pipefail

# ---------------------------------------------------------------------------
# Resolve repository root (the directory containing this script)
# ---------------------------------------------------------------------------
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$SCRIPT_DIR"

# ---------------------------------------------------------------------------
# Defaults
# ---------------------------------------------------------------------------
OUTPUT_DIR="$REPO_ROOT/freethreaded-packages"
CLEAN=0
UPLOAD=0
UPLOAD_USER=""
UPLOAD_LABEL="cp314t"

# ---------------------------------------------------------------------------
# Argument parsing
# ---------------------------------------------------------------------------
while [[ $# -gt 0 ]]; do
    case "$1" in
        --output-dir)
            OUTPUT_DIR="$(cd "$(dirname "$2")" 2>/dev/null && pwd)/$(basename "$2")" || OUTPUT_DIR="$2"
            shift 2
            ;;
        --clean)
            CLEAN=1
            shift
            ;;
        --upload)
            UPLOAD=1
            shift
            ;;
        --user)
            UPLOAD_USER="$2"
            shift 2
            ;;
        --label)
            UPLOAD_LABEL="$2"
            shift 2
            ;;
        -h|--help)
            sed -n '/^# Usage:/,/^[^#]/p' "$0" | head -n -1 | sed 's/^# \?//'
            exit 0
            ;;
        *)
            echo "Unknown argument: $1" >&2
            exit 1
            ;;
    esac
done

# ---------------------------------------------------------------------------
# Detect platform
# ---------------------------------------------------------------------------
OS="$(uname -s)"
ARCH="$(uname -m)"
case "$OS" in
    Linux*)   PLATFORM=linux ;;
    Darwin*)  PLATFORM=osx   ;;
    MINGW*|MSYS*|CYGWIN*) PLATFORM=win ;;
    *)
        echo "Unsupported OS: $OS" >&2
        exit 1
        ;;
esac

echo "==> Platform: $PLATFORM/$ARCH"
echo "==> Output dir: $OUTPUT_DIR"

# ---------------------------------------------------------------------------
# Ensure rattler-build is available
# ---------------------------------------------------------------------------
if ! command -v rattler-build &>/dev/null; then
    echo "==> rattler-build not found — installing via pixi..."
    if command -v pixi &>/dev/null; then
        pixi global install rattler-build
        # pixi global bin dir
        export PATH="$HOME/.pixi/bin:$PATH"
    else
        echo "==> pixi not found either — installing rattler-build into base conda env..."
        conda install -n base --yes -c conda-forge rattler-build
    fi
fi
RATTLER_BUILD="$(command -v rattler-build)"
echo "==> Using rattler-build: $RATTLER_BUILD ($($RATTLER_BUILD --version))"

# ---------------------------------------------------------------------------
# Write a platform-appropriate variant config for rattler-build.
# Two things are required:
#   1. c_stdlib / c_stdlib_version — resolves ${{ stdlib("c") }} in recipes
#   2. python: 3.14.* *_cp314t — forces the freethreaded Python ABI in the
#      host environment instead of the regular cp314 build.
# Values match conda-forge's own .ci_support files (see e.g.
# zstandard-feedstock/.ci_support/osx_arm64_python3.14.____cp314t.yaml).
# ---------------------------------------------------------------------------
VARIANT_CONFIG="$(mktemp /tmp/rattler-variants-XXXXXX.yaml)"
trap 'rm -f "$VARIANT_CONFIG"' EXIT

case "$PLATFORM" in
    linux)
        cat > "$VARIANT_CONFIG" << 'EOF'
c_stdlib:
  - sysroot
c_stdlib_version:
  - "2.17"
python:
  - "3.14.* *_cp314t"
EOF
        ;;
    osx)
        cat > "$VARIANT_CONFIG" << 'EOF'
c_stdlib:
  - macosx_deployment_target
c_stdlib_version:
  - "11.0"
python:
  - "3.14.* *_cp314t"
EOF
        ;;
    win)
        cat > "$VARIANT_CONFIG" << 'EOF'
c_stdlib:
  - vs
python:
  - "3.14.* *_cp314t"
EOF
        ;;
esac
echo "==> Variant config ($PLATFORM): $VARIANT_CONFIG"

# ---------------------------------------------------------------------------
# Clean if requested
# ---------------------------------------------------------------------------
if [[ $CLEAN -eq 1 && -d "$OUTPUT_DIR" ]]; then
    echo "==> Cleaning output directory: $OUTPUT_DIR"
    rm -rf "$OUTPUT_DIR"
fi
mkdir -p "$OUTPUT_DIR"

# ---------------------------------------------------------------------------
# Helper: build one or more recipes.
#
# NOTE on cross-recipe dependencies: rattler-build's build ordering (whether
# via multiple --recipe/-r flags or --recipe-dir) is a topological sort
# derived *only* from declared build/host/run requirements -- there is no
# "priority" setting to otherwise influence it (see
# https://github.com/prefix-dev/rattler-build/issues/2492 for a case where
# this ordering already has sharp edges). A genuine two-way requirement
# between two recipes is therefore not something rattler-build can resolve
# by itself, in one invocation or many: if A's build/test needs B and B's
# build/test needs A, there is no valid order.
#
# conda <-> conda-pypi is exactly this shape: conda's run requirements
# include conda-pypi, while conda-pypi's `downstream: conda` test (see
# threaded-recipes/conda-pypi/recipe.yaml) wants a working `conda`. We break
# the cycle by keeping conda-pypi's dependency on conda a *test-only*, soft
# one: conda-pypi is always built (and indexed) in its own invocation first,
# where `conda` legitimately isn't resolvable yet and its downstream test is
# just skipped; conda is then built in a later, separate invocation, by
# which point conda-pypi is already sitting in the local channel to satisfy
# conda's real dependency on it.
#
# In short: don't try to build conda and conda-pypi together (as one
# `rattler-build build` call, or via --recipe-dir over a directory
# containing both) -- keep them as separate, sequential build_recipes calls,
# in that order.
# ---------------------------------------------------------------------------
build_recipes() {
    local names=("$@")
    local recipe_args=()
    local name

    echo ""
    echo "==> Building ${names[*]}..."
    for name in "${names[@]}"; do
        recipe_args+=(--recipe "$REPO_ROOT/threaded-recipes/$name")
        echo "    recipe: $REPO_ROOT/threaded-recipes/$name"
    done

    local channel_args=()
    # Prepend the local output dir so previously built packages are available
    # (e.g. libmambapy can see menuinst if it were a dep, and to avoid
    # re-downloading already-built packages)
    channel_args+=(-c "file://${OUTPUT_DIR}")
    channel_args+=(-c conda-forge)

    "$RATTLER_BUILD" build \
        "${recipe_args[@]}" \
        --output-dir "$OUTPUT_DIR" \
        --variant-config "$VARIANT_CONFIG" \
        "${channel_args[@]}"
}

# ---------------------------------------------------------------------------
# Compute the version for the local `conda` build, the same way
# recipe/meta.yaml does: <tag>.<commits-since-tag>+<short-hash>
# (e.g. 26.7.0.69+g018d2fcde). Forwarded to threaded-recipes/conda/recipe.yaml
# via the CONDA_VERSION_OVERRIDE environment variable, since rattler-build
# has no git-describe jinja helpers of its own.
# ---------------------------------------------------------------------------
GIT_DESCRIBE_TAG="$(git -C "$REPO_ROOT" describe --tags --abbrev=0)"
GIT_DESCRIBE_NUMBER="$(git -C "$REPO_ROOT" rev-list "${GIT_DESCRIBE_TAG}..HEAD" --count)"
GIT_DESCRIBE_HASH="g$(git -C "$REPO_ROOT" rev-parse --short HEAD)"
export CONDA_VERSION_OVERRIDE="${GIT_DESCRIBE_TAG}.${GIT_DESCRIBE_NUMBER}+${GIT_DESCRIBE_HASH}"
echo "==> conda version: $CONDA_VERSION_OVERRIDE"

# ---------------------------------------------------------------------------
# Build each package
# ---------------------------------------------------------------------------
cd "$REPO_ROOT"

build_recipes pycosat
build_recipes menuinst
# libmambapy needs libmamba/libmamba-spdlog from conda-forge (already in channel_args)
build_recipes libmambapy
# conda-pypi first, on its own: its `downstream: conda` test can't resolve
# `conda` yet (it isn't built until the next line) and is simply skipped.
build_recipes conda-pypi
# conda's run deps (menuinst, pycosat, conda-pypi) must already be built
# above so they can be picked up from the local output channel.
build_recipes conda

if [[ "$PLATFORM" != "win" ]]; then
    build_recipes xonsh
else
    build_recipes pywin32
fi

# ---------------------------------------------------------------------------
# Index the local channel so conda can consume it
# ---------------------------------------------------------------------------
echo ""
echo "==> Indexing local channel: $OUTPUT_DIR"
conda index "$OUTPUT_DIR"

# ---------------------------------------------------------------------------
# Done
# ---------------------------------------------------------------------------
echo ""
echo "==> Done. Built packages:"
find "$OUTPUT_DIR" -name "*.conda" -o -name "*.tar.bz2" | sort | sed 's|^|    |'

echo ""
echo "==> To use this local channel, run the following from the repo root:"
echo ""
echo "    conda install \\"
echo "      --channel-priority strict \\"
echo "      --channel \"file://${OUTPUT_DIR}\" \\"
echo "      --channel conda-forge \\"
echo "      --file tests/requirements.txt \\"
echo "      --file tests/requirements-ci.txt \\"
echo "      --file tests/requirements-s3.txt \\"
if [[ "$PLATFORM" == "linux" ]]; then
echo "      xonsh patchelf \\"
elif [[ "$PLATFORM" == "win" ]]; then
echo "      pywin32 \\"
fi
echo "      \"conda=${CONDA_VERSION_OVERRIDE}\" \\"
echo "      python-freethreading=3.14"

# ---------------------------------------------------------------------------
# Optionally upload everything to anaconda.org
# ---------------------------------------------------------------------------
if [[ $UPLOAD -eq 1 ]]; then
    echo ""
    UPLOAD_ARGS=(--output-dir "$OUTPUT_DIR" --label "$UPLOAD_LABEL")
    if [[ -n "$UPLOAD_USER" ]]; then
        UPLOAD_ARGS+=(--user "$UPLOAD_USER")
    fi
    "$REPO_ROOT/upload-freethreaded-packages.sh" "${UPLOAD_ARGS[@]}"
fi
