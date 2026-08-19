#!/usr/bin/env bash
# build-freethreaded-deps.sh
#
# Builds cp314t (freethreaded Python 3.14) conda packages for the blockers
# that are missing cp314t builds on conda-forge:
#
#   pycosat, menuinst, libmambapy, xonsh (Linux/macOS), pywin32 (Windows)
#
# The built packages are placed in <repo-root>/freethreaded-packages/ and
# indexed as a local conda channel, ready for use with:
#
#   conda install --channel "file://$PWD/freethreaded-packages" ...
#
# Usage:
#   ./build-freethreaded-deps.sh [--output-dir <dir>] [--clean]
#
#   --output-dir <dir>  Where to write built packages (default: freethreaded-packages/)
#   --clean             Remove the output directory before building
#
# Requirements:
#   - conda (with conda-forge channel, e.g. miniforge)
#   - rattler-build  (installed automatically via pixi if missing)

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
# Helper: build one recipe
# ---------------------------------------------------------------------------
build_recipe() {
    local name="$1"
    local recipe_dir="$REPO_ROOT/threaded-recipes/$name"
    local extra_channels="${2:-}"

    echo ""
    echo "==> Building $name..."
    echo "    recipe: $recipe_dir"

    local channel_args=()
    # Prepend the local output dir so previously built packages are available
    # (e.g. libmambapy can see menuinst if it were a dep, and to avoid
    # re-downloading already-built packages)
    channel_args+=(-c "file://${OUTPUT_DIR}")
    if [[ -n "$extra_channels" ]]; then
        for ch in $extra_channels; do
            channel_args+=(-c "$ch")
        done
    fi
    channel_args+=(-c conda-forge)

    "$RATTLER_BUILD" build \
        --recipe "$recipe_dir" \
        --output-dir "$OUTPUT_DIR" \
        --variant-config "$VARIANT_CONFIG" \
        "${channel_args[@]}"
}

# ---------------------------------------------------------------------------
# Build each package
# ---------------------------------------------------------------------------
cd "$REPO_ROOT"

build_recipe pycosat
build_recipe menuinst
# libmambapy needs libmamba/libmamba-spdlog from conda-forge (already in channel_args)
build_recipe libmambapy

if [[ "$PLATFORM" != "win" ]]; then
    build_recipe xonsh
else
    build_recipe pywin32
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
echo "    # Strip the 'conda' package from requirements-ci.txt (it requires cp314, not cp314t)"
echo "    grep -v '^conda\b' tests/requirements-ci.txt > tests/requirements-ci-freethreaded.txt"
echo ""
echo "    conda install \\"
echo "      --channel-priority strict \\"
echo "      --channel \"file://${OUTPUT_DIR}\" \\"
echo "      --channel conda-forge \\"
echo "      --file tests/requirements.txt \\"
echo "      --file tests/requirements-ci-freethreaded.txt \\"
echo "      --file tests/requirements-s3.txt \\"
if [[ "$PLATFORM" == "linux" ]]; then
echo "      xonsh patchelf \\"
elif [[ "$PLATFORM" == "win" ]]; then
echo "      pywin32 \\"
fi
echo "      python-freethreading=3.14"
