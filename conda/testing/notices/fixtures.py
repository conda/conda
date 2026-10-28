# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""Collection of pytest fixtures used in conda.notices tests."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from ...base.constants import DEFAULTS_CHANNEL_NAME, NOTICES_CACHE_SUBDIR
from ...base.context import reset_context
from ...cli.conda_argparse import generate_parser

if TYPE_CHECKING:
    from collections.abc import Iterator
    from pathlib import Path
    from unittest.mock import MagicMock

    from pytest_mock import MockerFixture


@pytest.fixture(scope="function")
def notices_cache_dir(mocker: MockerFixture, tmp_path: Path) -> Iterator[Path]:
    """
    Fixture that creates the notices cache dir while also mocking
    out a call to user_cache_dir.
    """
    mocker.patch("conda.notices.cache.user_cache_dir", return_value=tmp_path)
    cache_dir = tmp_path / NOTICES_CACHE_SUBDIR
    cache_dir.mkdir(parents=True, exist_ok=True)

    yield cache_dir


@pytest.fixture(scope="function")
def notices_mock_fetch_get_session(mocker: MockerFixture) -> MagicMock:
    return mocker.patch("conda.notices.fetch.get_session")


@pytest.fixture(scope="function")
def conda_notices_args_n_parser():
    parser = generate_parser()
    args = parser.parse_args(["notices", f"--channel={DEFAULTS_CHANNEL_NAME}"])
    reset_context((), args)

    return args, parser
