# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
import json
from typing import Iterable

import pytest

from conda.base.context import context
from conda.testing import CondaCLIFixture


@pytest.mark.parametrize(
    "args",
    [
        pytest.param(("--get",), id="get, user"),
        pytest.param(
            ("--get", "--system"),
            id="get, system",
            mark=pytest.mark.skip(not context.root_writable),
        ),
        pytest.param(("--get", "--file", "missing"), id="get, provided"),
        pytest.param(("--get", "channels"), id="key, user"),
        pytest.param(
            ("--get", "channels", "--system"),
            id="key, system",
            mark=pytest.mark.skip(not context.root_writable),
        ),
        pytest.param(("--get", "channels", "--file", "missing"), id="key, provided"),
        pytest.param(("--get", "use_pip"), id="unknown, user"),
        pytest.param(
            ("--get", "use_pip", "--system"),
            id="unknown, system",
            mark=pytest.mark.skip(not context.root_writable),
        ),
        pytest.param(("--get", "use_pip", "--file", "missing"), id="unknown, provided"),
    ],
)
def test_config(conda_cli: CondaCLIFixture, args: Iterable[str]):
    stdout, _, _ = conda_cli("config", "--json", *args)
    parsed = json.loads(stdout.strip())
    assert "get" in parsed
    assert "rc_path" in parsed
    assert parsed["success"]
    assert "warnings" in parsed
