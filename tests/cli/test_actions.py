# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
from __future__ import annotations

from argparse import ArgumentParser
from contextlib import nullcontext
from typing import TYPE_CHECKING

import pytest

from conda.cli import actions
from conda.cli.actions import NullCountAction
from conda.common.constants import NULL

if TYPE_CHECKING:
    from typing import Any


def test_null_count_action():
    parser = ArgumentParser()
    parser.add_argument("--verbose", action=NullCountAction, default=NULL)
    args = parser.parse_args([])
    assert args.verbose is NULL
    args = parser.parse_args(["--verbose"])
    assert args.verbose == 1
    args = parser.parse_args(["--verbose", "--verbose"])
    assert args.verbose == 2
    args = parser.parse_args(["--verbose", "--verbose", "--verbose"])
    assert args.verbose == 3


@pytest.mark.parametrize(
    "function,raises",
    [
        ("NullCountAction._ensure_value", TypeError),
    ],
)
def test_deprecations(function: str, raises: type[Exception] | None):
    *names, function = function.split(".")
    node: Any = actions
    for name in names:
        node = getattr(node, name)
    raises_context = pytest.raises(raises) if raises else nullcontext()
    with pytest.deprecated_call(), raises_context:
        getattr(node, function)()
