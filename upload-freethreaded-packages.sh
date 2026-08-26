#!/usr/bin/env bash
# upload-freethreaded-packages.sh
#
# Uploads all conda packages (*.conda / *.tar.bz2) built by
# build-freethreaded-deps.sh to an anaconda.org account/organization using
# anaconda-client, so others can test the freethreaded (cp314t) builds via:
#
#   conda install --channel <user>/label/<label> --channel conda-forge ...
#
# Usage:
#   ./upload-freethreaded-packages.sh [--output-dir <dir>] [--user <user>]
#                                      [--label <label>] [--force] [--dry-run]
#
#   --output-dir <dir>  Where the built packages live (default: freethreaded-packages/)
#   --user <user>       anaconda.org user/org to upload to (default: current
#                        anaconda-client user, i.e. whatever "anaconda whoami" reports)
#   --label <label>     anaconda.org label to upload to (default: cp314t)
#   --force             Pass --force to `anaconda upload` (re-upload/overwrite
#                        files that already exist on anaconda.org)
#   --dry-run           Print the packages that would be uploaded without uploading
#
# Requirements:
#   - anaconda-client, already authenticated (`anaconda login`) or with
#     ANACONDA_API_TOKEN set in the environment.

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
UPLOAD_USER=""
UPLOAD_LABEL="cp314t"
FORCE=0
DRY_RUN=0

# ---------------------------------------------------------------------------
# Argument parsing
# ---------------------------------------------------------------------------
while [[ $# -gt 0 ]]; do
    case "$1" in
        --output-dir)
            OUTPUT_DIR="$(cd "$(dirname "$2")" 2>/dev/null && pwd)/$(basename "$2")" || OUTPUT_DIR="$2"
            shift 2
            ;;
        --user)
            UPLOAD_USER="$2"
            shift 2
            ;;
        --label)
            UPLOAD_LABEL="$2"
            shift 2
            ;;
        --force)
            FORCE=1
            shift
            ;;
        --dry-run)
            DRY_RUN=1
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
# Ensure anaconda-client is available
# ---------------------------------------------------------------------------
if ! command -v anaconda &>/dev/null; then
    echo "==> anaconda-client (the 'anaconda' command) not found." >&2
    echo "    Install it with: conda install -n base --yes -c conda-forge anaconda-client" >&2
    exit 1
fi

if [[ ! -d "$OUTPUT_DIR" ]]; then
    echo "Output directory not found: $OUTPUT_DIR" >&2
    echo "Run build-freethreaded-deps.sh first, or pass --output-dir." >&2
    exit 1
fi

# ---------------------------------------------------------------------------
# Collect built packages (skip repodata/index files, only real packages)
# ---------------------------------------------------------------------------
mapfile -t PACKAGES < <(find "$OUTPUT_DIR" \( -name "*.conda" -o -name "*.tar.bz2" \) | sort)

if [[ ${#PACKAGES[@]} -eq 0 ]]; then
    echo "No .conda/.tar.bz2 packages found under: $OUTPUT_DIR" >&2
    exit 1
fi

echo "==> Found ${#PACKAGES[@]} package(s) to upload from: $OUTPUT_DIR"
printf '    %s\n' "${PACKAGES[@]}"

if [[ $DRY_RUN -eq 1 ]]; then
    echo ""
    echo "==> --dry-run set, not uploading."
    exit 0
fi

# ---------------------------------------------------------------------------
# Upload
# ---------------------------------------------------------------------------
UPLOAD_ARGS=(--label "$UPLOAD_LABEL" --no-progress --register)
if [[ -n "$UPLOAD_USER" ]]; then
    UPLOAD_ARGS+=(--user "$UPLOAD_USER")
fi
if [[ $FORCE -eq 1 ]]; then
    UPLOAD_ARGS+=(--force)
fi

echo ""
echo "==> Uploading to anaconda.org (label: ${UPLOAD_LABEL})..."
anaconda upload "${UPLOAD_ARGS[@]}" "${PACKAGES[@]}"

# ---------------------------------------------------------------------------
# Done
# ---------------------------------------------------------------------------
WHOAMI_USER="${UPLOAD_USER:-$(anaconda whoami 2>/dev/null | awk '/Username/ {print $2}')}"
echo ""
echo "==> Done. Testers can install these builds with, e.g.:"
echo ""
echo "    conda install \\"
echo "      --channel-priority strict \\"
echo "      --channel ${WHOAMI_USER:-<your-username>}/label/${UPLOAD_LABEL} \\"
echo "      --channel conda-forge \\"
echo "      conda python-freethreading=3.14"
