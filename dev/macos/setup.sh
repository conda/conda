#!/usr/bin/env bash

set -o errtrace -o pipefail -o errexit

eval "$(python -m conda init bash --dev)"
