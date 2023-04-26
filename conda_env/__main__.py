# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
import sys

from conda.deprecations import deprecated

from .cli.main import main

deprecated.module("23.9", "24.3", addendum="Use `conda env` instead.")

sys.exit(main())
