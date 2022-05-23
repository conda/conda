# -*- coding: utf-8 -*-
# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause

import pytest

from conda.base.context import reset_context

# Unused imports ensure these fixtures are available in this module:
# https://docs.pytest.org/en/6.2.x/fixture.html#conftest-py-sharing-fixtures-across-multiple-files
from tests.notices.conftest import notices_cache_dir, notices_mock_http_session_get


@pytest.fixture(scope="function")
def reset_conda_context():
    """
    Resets the context object after each test function is run.
    """
    yield

    reset_context()
