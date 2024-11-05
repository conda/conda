# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
from __future__ import annotations

import json
import re
from typing import TYPE_CHECKING

import pytest
import requests

from conda.base.context import context, reset_context
from conda.cli.main_search import _pretty_record_format, pretty_record
from conda.exceptions import PackagesNotFoundError
from conda.gateways.anaconda_client import read_binstar_tokens
from conda.models.records import PackageRecord

if TYPE_CHECKING:
    from pathlib import Path

    from pytest import CaptureFixture, MonkeyPatch

    from conda.testing.fixtures import CondaCLIFixture

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


def test_current_platform_package_missing(
    test_recipes_channel: Path,
    conda_cli: CondaCLIFixture,
):
    with pytest.raises(PackagesNotFoundError):
        conda_cli("search", "arch-package", "--json")


def test_mocked_platform_package_found(
    monkeypatch: MonkeyPatch,
    test_recipes_channel: Path,
    conda_cli: CondaCLIFixture,
):
    # mock a different subdir
    monkeypatch.setenv("CONDA_SUBDIR", "linux-fake")
    reset_context()
    assert context.subdir == "linux-fake"

    stdout, stderr, err = conda_cli("search", "arch-package", "--json")
    json_obj = json.loads(stdout.strip())
    assert len(json_obj) == 1
    assert json_obj["arch-package"]
    assert not stderr
    assert not err


def test_different_platform_package_found(
    test_recipes_channel: Path,
    conda_cli: CondaCLIFixture,
):
    stdout, stderr, err = conda_cli(
        "search",
        "--platform=linux-fake",
        "arch-package",
        "--json",
    )
    json_obj = json.loads(stdout.strip())
    assert len(json_obj) == 1
    assert json_obj["arch-package"]
    assert not stderr
    assert not err


def test_unknown_platform_package_missing(
    test_recipes_channel: Path,
    conda_cli: CondaCLIFixture,
):
    with pytest.raises(PackagesNotFoundError):
        conda_cli("search", "--platform=linux-unknown", "arch-package", "--json")


@pytest.mark.skipif(
    read_binstar_tokens(),
    reason="binstar token found in global configuration",
)
def test_anaconda_token_with_private_package(
    conda_cli: CondaCLIFixture,
    capsys: CaptureFixture,
):
    # TODO: should also write a test to use binstar_client to set the token,
    # then let conda load the token
    package = "private-package"

    # Step 1. Make sure without the token we don't see the package
    channel_url = "https://conda-web.anaconda.org/conda-test"
    with pytest.raises(PackagesNotFoundError):
        conda_cli("search", f"--channel={channel_url}", package)
    # flush stdout/stderr
    capsys.readouterr()

    # Step 2. Now with the token make sure we can see the package
    channel_url = "https://conda-web.anaconda.org/t/co-de3376bc-5463-41fe-8d14-878c7e6a8253/conda-test"
    stdout, _, _ = conda_cli(
        "search",
        f"--channel={channel_url}",
        package,
        "--json",
    )
    assert package in json.loads(stdout)


def test_bad_anaconda_token(monkeypatch: MonkeyPatch, conda_cli: CondaCLIFixture):
    # This test changed around 2017-10-17, when the behavior of anaconda.org
    # was changed.  Previously, an expired token would return with a 401 response.
    # Now, a 200 response is always given, with any public packages available on the channel.
    channel_url = "https://conda.anaconda.org/t/cqgccfm1mfma/data-portal"
    response = requests.get(f"{channel_url}/{context.subdir}/repodata.json")
    assert response.status_code == 200

    with pytest.raises(PackagesNotFoundError):
        # this was supposed to be a package available in private but not
        # public data-portal; boltons was added to defaults in 2023 Jan.
        # --override-channels instead.
        conda_cli(
            "search",
            "--override-channels",
            f"--channel={channel_url}",
            "boltons",
            "--json",
        )

    stdout, stderr, _ = conda_cli(
        "search",
        "--override-channels",
        f"--channel={channel_url}",
        "anaconda-mosaic",
        "--json",
    )
    json_obj = json.loads(stdout)
    assert "anaconda-mosaic" in json_obj
    assert len(json_obj["anaconda-mosaic"]) > 0


def test_pretty_record():
    """
    Coverage for missing/None fields in PackageRecord
    """
    args = []

    def print(arg):
        args.append(arg)

    pretty_record(
        PackageRecord.from_objects(
            {
                "name": "p",
                "version": "1",
                "build": "1",
                "build_number": 1,
                "timestamp": 0,
                "license": None,
            }
        ),
        print=print,
    )

    # subdir will change, check everything up to that point
    assert "\n".join(args).startswith(
        "p 1 1\n-----\nfile name   : p-1-1\nname        : p\nversion     : 1\nbuild       : 1\nbuild number: 1\nsubdir      :"
    )

    # cover timestamp, size, constrains lines
    with_timestamp_and_constrains = _pretty_record_format(
        PackageRecord.from_objects(
            {
                "name": "p",
                "version": "1",
                "build": "1",
                "build_number": 1,
                "timestamp": 1,
                "license": None,
                "constrains": ["conda"],
                "size": 1,
            }
        )
    )

    assert with_timestamp_and_constrains.startswith("p 1 1\n")
