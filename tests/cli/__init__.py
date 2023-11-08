# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
import logging

import pytest


@pytest.fixture(autouse=True)
def urllib3_logger_error(caplog):
    "Increasing the level to error to prevent retries show up in the stderr"
    caplog.set_level(logging.ERROR, logger="urllib3.connectionpool")
