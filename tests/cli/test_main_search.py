# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
import json
import re

import pytest
from pytest import MonkeyPatch

from conda.base.context import context, reset_context
from conda.exceptions import PackagesNotFoundError
from conda.testing import CondaCLIFixture

# all tests in this file are integration tests
pytestmark = [pytest.mark.integration]


@pytest.mark.flaky(reruns=5)
def test_search_0(conda_cli: CondaCLIFixture):
    # searching for everything is quite slow; search without name, few
    # matching packages. py_3 is not a special build tag, but there are just
    # a few of them in defaults.
    stdout, stderr, err = conda_cli(
        "search",
        "*[build=py_3]",
        "--json",
        "--override-channels",
        "--channel",
        "defaults",
    )
    assert not stderr
    assert not err

    parsed = json.loads(stdout.strip())

    # happens to have py_3 build in noarch
    package_name = "pydotplus"

    assert isinstance(parsed, dict)
    assert isinstance(parsed[package_name], list)
    assert isinstance(parsed[package_name][0], dict)
    assert {"build", "channel", "fn", "version"} <= set(parsed[package_name][0])
    assert parsed[package_name][0]["build"] == "py_3"


@pytest.mark.flaky(reruns=5)
def test_search_1(conda_cli: CondaCLIFixture):
    stdout, stderr, err = conda_cli(
        "search",
        "ipython",
        "--json",
        "--override-channels",
        "--channel",
        "defaults",
    )
    parsed = json.loads(stdout.strip())
    assert isinstance(parsed, dict)
    assert not stderr
    assert not err


@pytest.mark.parametrize(
    "package",
    [
        pytest.param("python", id="exact"),
        pytest.param("ython", id="wildcard"),
    ],
)
@pytest.mark.flaky(reruns=5)
def test_search_2(conda_cli: CondaCLIFixture, package: str):
    stdout, stderr, err = conda_cli(
        "search",
        package,
        "--override-channels",
        "--channel",
        "defaults",
    )
    # python                        3.8.11      hbdb9e5c_5  pkgs/main
    assert re.search(r"(python)\s+(\d+\.\d+\.\d+)\s+(\w+)\s+(pkgs/main)", stdout)
    assert not stderr
    assert not err


@pytest.mark.flaky(reruns=5)
def test_search_3(conda_cli: CondaCLIFixture):
    stdout, stderr, err = conda_cli(
        "search",
        "*/linux-64::nose==1.3.7[build=py37_2]",
        "--info",
        "--override-channels",
        "--channel",
        "defaults",
    )
    assert "file name   : nose-1.3.7-py37_2" in stdout
    assert "name        : nose" in stdout
    assert "version     : 1.3.7" in stdout
    assert "build       : py37_2" in stdout
    assert "build number: 2" in stdout
    assert "subdir      : linux-64" in stdout
    assert (
        "url         : https://repo.anaconda.com/pkgs/main/linux-64/nose-1.3.7-py37_2"
        in stdout
    )
    assert not stderr
    assert not err


@pytest.mark.flaky(reruns=5)
def test_search_4(conda_cli: CondaCLIFixture):
    stdout, stderr, err = conda_cli(
        "search",
        "--json",
        "--override-channels",
        "--channel",
        "defaults",
        "--use-index-cache",
        "python",
    )
    parsed = json.loads(stdout.strip())
    assert isinstance(parsed, dict)
    assert not stderr
    assert not err


@pytest.mark.flaky(reruns=5)
def test_search_5(conda_cli: CondaCLIFixture):
    stdout, stderr, err = conda_cli(
        "search",
        "--platform",
        "win-32",
        "--json",
        "--override-channels",
        "--channel",
        "defaults",
        "python",
    )
    parsed = json.loads(stdout.strip())
    assert isinstance(parsed, dict)
    assert not stderr
    assert not err


def test_search_envs(conda_cli: CondaCLIFixture):
    # search environments for Python (will be present in testing env)
    stdout, _, _ = conda_cli("search", "--envs", "python")
    assert "Searching environments" in stdout
    assert "python" in stdout


def test_search_envs_info(conda_cli: CondaCLIFixture):
    # search environments for Python (will be present in testing env)
    stdout, _, _ = conda_cli("search", "--envs", "--info", "python")
    assert "Searching environments" in stdout
    assert "python" in stdout


def test_search_envs_json(conda_cli: CondaCLIFixture):
    # search environments for Python (will be present in testing env)
    search_for = "python"
    stdout, _, _ = conda_cli("search", "--envs", "--json", search_for)
    assert "Searching environments" not in stdout
    parsed = json.loads(stdout.strip())
    assert isinstance(parsed, list)  # can be [] if package not found
    assert len(parsed), "empty search result"
    assert all(entry["package_records"][0]["name"] == search_for for entry in parsed)


@pytest.mark.flaky(reruns=5)
def test_search_inflexible(conda_cli: CondaCLIFixture):
    # 'r-rcpparmadill' should not be found
    with pytest.raises(PackagesNotFoundError) as excinfo:
        _ = conda_cli(
            "search",
            "--platform",
            "linux-64",
            "--override-channels",
            "--channel",
            "defaults",
            "--skip-flexible-search",
            "r-rcpparmadill",
        )
    # check that failure wasn't from flexible mode
    assert "*r-rcpparmadill*" not in str(excinfo.value)


@pytest.mark.parametrize(
    "subdir",
    ("linux-32", "linux-64", "osx-64", "win-32", "win-64"),
)
def test_rpy_search(monkeypatch: MonkeyPatch, conda_cli: CondaCLIFixture, subdir: str):
    monkeypatch.setenv("CONDA_SUBDIR", subdir)
    reset_context()
    assert context.subdir == subdir

    # assert conda search cannot find rpy2
    with pytest.raises(PackagesNotFoundError):
        conda_cli("search", "--override-channels", "--channel=main", "rpy2")

    # assert conda search can now find rpy2
    stdout, stderr, _ = conda_cli(
        "search",
        "--override-channels",
        "--channel=r",
        "rpy2",
        "--json",
    )
    assert "rpy2" in json.loads(stdout)
