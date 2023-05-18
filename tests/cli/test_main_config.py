# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
import json
from pathlib import Path
from typing import Iterable

import pytest

from conda.base.context import context
from conda.testing import CondaCLIFixture, PathFactoryFixture


@pytest.mark.parametrize(
    "args",
    [
        pytest.param(("--get",), id="get"),
        pytest.param(("--get", "channels"), id="key"),
        pytest.param(("--get", "use_pip"), id="unknown"),
    ],
)
def test_config_get_user(conda_cli: CondaCLIFixture, args: Iterable[str]):
    stdout, _, _ = conda_cli("config", "--json", *args)
    parsed = json.loads(stdout.strip())
    assert "get" in parsed
    assert "rc_path" in parsed
    assert parsed["success"]
    assert "warnings" in parsed


@pytest.mark.skipif(not context.root_writable, reason="not root writable")
@pytest.mark.parametrize(
    "args",
    [
        pytest.param(("--get",), id="get"),
        pytest.param(("--get", "channels"), id="key"),
        pytest.param(("--get", "use_pip"), id="unknown"),
    ],
)
def test_config_get_system(conda_cli: CondaCLIFixture, args: Iterable[str]):
    stdout, _, _ = conda_cli("config", "--json", *args, "--system")
    parsed = json.loads(stdout.strip())
    assert "get" in parsed
    assert "rc_path" in parsed
    assert parsed["success"]
    assert "warnings" in parsed


@pytest.mark.parametrize(
    "args",
    [
        pytest.param(("--get",), id="get"),
        pytest.param(("--get", "channels"), id="key"),
        pytest.param(("--get", "use_pip"), id="unknown"),
    ],
)
def test_config_get_missing(
    conda_cli: CondaCLIFixture,
    args: Iterable[str],
    path_factory: PathFactoryFixture,
):
    path = path_factory()
    stdout, _, _ = conda_cli("config", "--json", *args, "--file", path)
    parsed = json.loads(stdout.strip())
    assert parsed["get"] == {}
    assert Path(parsed["rc_path"]) == path
    assert parsed["success"]
    assert "warnings" in parsed
