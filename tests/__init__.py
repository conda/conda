# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
# This is just here so that tests is a package, so that dotted relative
# imports work.
from conda.gateways.logging import initialize_logging

initialize_logging()

from conda.testing import conda_move_to_front_of_PATH

conda_move_to_front_of_PATH()
