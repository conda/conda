# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
from __future__ import annotations

from argparse import ArgumentParser
from contextlib import nullcontext
from typing import TYPE_CHECKING

import pytest

from conda.cli import actions
from conda.cli.actions import LazyAction, NullCountAction
from conda.common.constants import NULL

if TYPE_CHECKING:
    from typing import Any

    from pytest_mock import MockerFixture


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


@pytest.mark.parametrize(
    "kwargs,match",
    [
        (
            {"choices": ["a"], "choices_factory": lambda: ["b"]},
            "choices and choices_factory",
        ),
        ({"help": "a", "help_factory": lambda: "b"}, "help and help_factory"),
    ],
)
def test_lazy_action_mutually_exclusive(kwargs: dict, match: str):
    with pytest.raises(ValueError, match=match):
        LazyAction(option_strings=["--x"], dest="x", **kwargs)


@pytest.mark.parametrize(
    "key,value",
    [
        ("choices", ["a"]),
        ("help", "a"),
    ],
)
def test_lazy_action_factory(mocker: MockerFixture, key: str, value: Any):
    factory = mocker.Mock(return_value=value)
    action = LazyAction(
        option_strings=["--x"],
        dest="x",
        **{f"{key}_factory": factory},
    )

    # initially uncalled
    assert factory.call_count == 0

    # first call is evaluated
    assert getattr(action, key) == value
    assert factory.call_count == 1

    # second call is cached
    assert getattr(action, key) == value
    assert factory.call_count == 1
