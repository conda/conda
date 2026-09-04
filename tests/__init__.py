# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
# This is just here so that tests is a package, so that dotted relative
# imports work.

import sys

from conda.gateways.logging import initialize_logging

initialize_logging()

from conda.testing import conda_move_to_front_of_PATH

conda_move_to_front_of_PATH()

from pathlib import Path

TEST_RECIPES_CHANNEL = Path(__file__).parent / "data" / "test-recipes"

PYTHON_SPEC = f"python={sys.version_info.major}.{sys.version_info.minor}"
"""MatchSpec for the conda ``python`` package in integration tests.

Pinning to the same **major.minor** as :py:data:`sys.version_info` (the
interpreter running pytest) improves odds of reusing cached ``python``
package.

This does **not** define conda's highest supported Python version.
"""

PYTHON_SPEC_OLD = f"python={sys.version_info.major}.{sys.version_info.minor - 1}"
"""MatchSpec for one minor **below** :data:`PYTHON_SPEC` (same major).

For tests that need two distinct conda Python minors (e.g., upgrade).

This does **not** define conda's lowest supported Python version.
"""
