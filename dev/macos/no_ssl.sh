#!/usr/bin/env bash

set -o errtrace -o pipefail -o errexit

eval "$(sudo python -m conda init bash --dev)"
conda info
pytest -v tests_no_ssl
