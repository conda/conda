# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
import json
from os.path import isdir

import pytest

from conda.common.io import env_var
from conda.testing import CondaCLIFixture


# conda info --root [--json]
def test_info_root(reset_conda_context: None, conda_cli: CondaCLIFixture):
    stdout, stderr, err = conda_cli("info", "--root")
    assert isdir(stdout.strip())
    assert not stderr
    assert not err

    stdout, stderr, err = conda_cli("info", "--root", "--json")
    parsed = json.loads(stdout.strip())
    assert isdir(parsed["root_prefix"])
    assert not stderr
    assert not err


# conda info --unsafe-channels [--json]
def test_info_unsafe_channels(reset_conda_context: None, conda_cli: CondaCLIFixture):
    url = "https://conda.anaconda.org/t/tk-123/a/b/c"
    with env_var("CONDA_CHANNELS", url):
        stdout, stderr, err = conda_cli("info", "--unsafe-channels")
        assert "tk-123" in stdout
        assert not stderr
        assert not err

        stdout, stderr, err = conda_cli("info", "--unsafe-channels", "--json")
        parsed = json.loads(stdout.strip())
        assert url in parsed["channels"]
        assert not stderr
        assert not err


# conda info --verbose | --envs | --system
def test_info(conda_cli: CondaCLIFixture):
    stdout_basic, stderr, err = conda_cli("info")
    assert "platform" in stdout_basic
    assert "conda version" in stdout_basic
    assert "envs directories" in stdout_basic
    assert "package cache" in stdout_basic
    assert "channel URLs" in stdout_basic
    assert "config file" in stdout_basic
    assert "offline mode" in stdout_basic
    assert "solver" in stdout_basic
    assert not stderr
    assert not err

    stdout_envs, stderr, err = conda_cli("info", "--envs")
    assert "base" in stdout_envs
    assert not stderr
    assert not err

    stdout_sys, stderr, err = conda_cli("info", "--system")
    assert "sys.version" in stdout_sys
    assert "sys.prefix" in stdout_sys
    assert "sys.executable" in stdout_sys
    assert "conda location" in stdout_sys
    assert "conda-build" in stdout_sys
    assert "PATH" in stdout_sys
    assert not stderr
    assert not err

    stdout_all, stderr, err = conda_cli("info", "--verbose")
    assert stdout_basic in stdout_all
    assert stdout_envs in stdout_all
    assert stdout_sys in stdout_all
    assert not stderr
    assert not err


# conda info --all
def test_info_all(conda_cli: CondaCLIFixture):
    with pytest.warns(
        DeprecationWarning,
        match="`--all` is deprecated and will be removed in 24.9. Use `--verbose` instead.",
    ):
        conda_cli("info", "--all")


# conda info --json
def test_info_json(conda_cli: CondaCLIFixture):
    stdout, _, _ = conda_cli("info", "--json")
    parsed = json.loads(stdout.strip())
    assert isinstance(parsed, dict)

    # assert all keys are present
    assert {
        "channels",
        "conda_version",
        "default_prefix",
        "envs",
        "envs_dirs",
        "pkgs_dirs",
        "platform",
        "python_version",
        "rc_path",
        "root_prefix",
        "root_writable",
        "solver",
    } <= set(parsed)
