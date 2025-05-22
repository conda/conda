# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause

import pytest

from conda.env.env import Environment
from conda.env.specs.pixi_lock_file import PixiLockFile
from conda.exceptions import CondaError

from .. import support_file


def test_no_environment_file():
    spec = PixiLockFile(filename="not-a-file")
    assert not spec.can_handle()


def test_invalid_yaml_file(tmp_path):
    invalid_yaml = tmp_path / "invalid.lock"
    invalid_yaml.write_text("foo: {")
    spec = PixiLockFile(filename=str(invalid_yaml))
    assert not spec.can_handle()


def test_non_yaml_file(tmp_path):
    non_yaml = tmp_path / "non_yaml.lock"
    non_yaml.write_text("TEXT")
    spec = PixiLockFile(filename=str(non_yaml))
    assert not spec.can_handle()


def test_environment():
    spec = PixiLockFile(filename=support_file("pixi.lock"), platform="osx-arm64")
    assert isinstance(spec.environment, Environment)
    assert "conda_direct" in spec.environment.dependencies
    assert "pip_direct" in spec.environment.dependencies
    assert (
        "https://conda.anaconda.org/conda-forge/osx-arm64/bzip2-1.0.8-h99b78c6_7.conda"
        in spec.environment.dependencies["conda_direct"]
    )
    assert (
        "https://files.pythonhosted.org/packages/ff/62/85c4c919272577931d407be5ba5d71c20f0b616d31a0befe0ae45bb79abd/imagesize-1.4.1-py2.py3-none-any.whl"
        in spec.environment.dependencies["pip_direct"]
    )


def test_no_lock_environment_name():
    spec = PixiLockFile(
        filename=support_file("pixi.lock"),
        lock_environment_name="not-a-environment",
        platform="osx-arm64",
    )
    with pytest.raises(CondaError):
        spec.environment


def test_no_platform():
    spec = PixiLockFile(
        filename=support_file("pixi.lock"),
        platform="linux-64",
    )
    with pytest.raises(CondaError):
        spec.environment
