# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
from contextlib import nullcontext
from logging import getLogger

import pytest

from conda.base import constants
from conda.base.constants import ChannelPriority
from conda.common.constants import NULL

log = getLogger(__name__)


def test_null_is_falsey():
    assert not NULL


def test_ChannelPriority():
    assert ChannelPriority("strict") == ChannelPriority.STRICT
    assert ChannelPriority["STRICT"] == ChannelPriority.STRICT
    assert ChannelPriority(False) == ChannelPriority.DISABLED
    assert ChannelPriority("false") == ChannelPriority.DISABLED


@pytest.mark.parametrize(
    "function,raises",
    [
        ("ERROR_UPLOAD_URL", TypeError),
        ("CONDA_PACKAGE_EXTENSIONS", TypeError),
        ("CONDA_PACKAGE_PARTS", TypeError),
    ],
)
def test_deprecations(function: str, raises: type[Exception] | None) -> None:
    raises_context = pytest.raises(raises) if raises else nullcontext()
    with pytest.deprecated_call(), raises_context:
        getattr(constants, function)()
