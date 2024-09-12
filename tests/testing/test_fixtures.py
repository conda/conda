# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
from __future__ import annotations

import sys
from typing import TYPE_CHECKING

from conda.base.context import context, reset_context
from conda.gateways.disk.test import is_conda_environment

if TYPE_CHECKING:
    from pathlib import Path

    from _pytest.capture import MultiCapture
    from pytest import MonkeyPatch, Pytester

    from conda.testing.fixtures import (
        CondaCLIFixture,
        PathFactoryFixture,
        TmpChannelFixture,
        TmpEnvFixture,
    )

pytest_plugins = ["conda.testing.fixtures", "pytester"]


def test_global_capsys(global_capsys: MultiCapture) -> None:
    print("stdout")
    print("stderr", file=sys.stderr)
    out, err = global_capsys.readouterr()
    assert out == "stdout\n"
    assert err == "stderr\n"


def test_conda_cli(conda_cli: CondaCLIFixture) -> None:
    stdout, stderr, err = conda_cli("info")
    assert stdout
    assert not stderr
    assert not err


def test_global_conda_cli(global_conda_cli: CondaCLIFixture) -> None:
    stdout, stderr, err = global_conda_cli("info")
    assert stdout
    assert not stderr
    assert not err


def test_path_factory(path_factory: PathFactoryFixture) -> None:
    path = path_factory()
    assert not path.exists()
    assert path.parent.is_dir()


def test_tmp_env(tmp_env: TmpEnvFixture) -> None:
    with tmp_env() as prefix:
        is_conda_environment(prefix)


def test_global_tmp_env(global_tmp_env: TmpEnvFixture) -> None:
    with global_tmp_env() as prefix:
        is_conda_environment(prefix)


def test_env(pytester: Pytester) -> None:
    """Assert all tests get the same conda environment."""
    pytester.makepyfile(
        """
        import pytest

        pytest_plugins = "conda.testing.fixtures"

        @pytest.fixture
        def env1(tmp_env):
            with tmp_env() as prefix:
                yield prefix

        @pytest.fixture(scope="session")
        def env2(global_tmp_env):
            with global_tmp_env() as prefix:
                yield prefix

        @pytest.fixture(scope="session")
        def env3(global_tmp_env):
            with global_tmp_env() as prefix:
                yield prefix

        NAME = None

        def test_env1(env1):
            global NAME
            NAME = env1.name
            assert env1.name != "tmp_env-0"

        def test_env2(env1):
            assert env1.name != "tmp_env-0"
            assert env1.name != NAME

        def test_env3(env2):
            assert env2.name == "tmp_env-0"

        def test_env4(env2):
            assert env2.name == "tmp_env-0"

        def test_env5(env3):
            assert env3.name == "tmp_env-1"

        def test_env6(env3):
            assert env3.name == "tmp_env-1"
        """
    )
    result = pytester.runpytest()
    result.assert_outcomes(passed=6)


def test_tmp_channel(tmp_channel: TmpChannelFixture) -> None:
    with tmp_channel() as (channel, url):
        assert channel.is_dir()


def test_monkeypatch(monkeypatch: MonkeyPatch) -> None:
    monkeypatch.setenv("CONDA_CLOBBER", "true")
    reset_context()
    assert context.clobber


def test_tmp_pkgs_dir(tmp_pkgs_dir: Path) -> None:
    assert tmp_pkgs_dir.is_dir()


def test_tmp_envs_dir(tmp_envs_dir: Path) -> None:
    assert tmp_envs_dir.is_dir()
