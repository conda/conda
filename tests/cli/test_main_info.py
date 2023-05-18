# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
import json
from os.path import isdir

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
    } <= set(parsed)


# DEPRECATED: conda info PACKAGE --json
def test_info_conda_json(conda_cli: CondaCLIFixture):
    stdout, _, _ = conda_cli("info", "conda", "--json")
    parsed = json.loads(stdout.strip())
    assert isinstance(parsed, dict)
    assert "conda" in parsed
    assert isinstance(parsed["conda"], list)
