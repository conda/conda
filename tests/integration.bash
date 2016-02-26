set -eu

HERE="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$HERE"

build() {
    conda install --yes conda-build

    export GIT_DESCRIBE_TAG="0.0.0"
    conda build ../conda.recipe
    conda clean --yes --tarballs --index-cache --packages
}

main() {
    build
    conda install --yes --channel kalefranz bats
    bats integration
}

main
