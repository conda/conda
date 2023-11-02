# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
import importlib
import random
from unittest import mock

from conda.env import env
from conda.env.specs.yaml_file import YamlFileSpec


def test_no_environment_file():
    spec = YamlFileSpec(name=None, filename="not-a-file")
    assert not spec.can_handle()


def test_environment_file_exist():
    with mock.patch.object(env, "from_file", return_value={}):
        spec = YamlFileSpec(name=None, filename="environment.yaml")
        assert spec.can_handle()


def test_get_environment():
    r = random.randint(100, 200)
    with mock.patch.object(env, "from_file", return_value=r):
        spec = YamlFileSpec(name=None, filename="environment.yaml")
        assert spec.environment == r


def test_filename():
    filename = f"filename_{random.randint(100, 200)}"
    with mock.patch.object(env, "from_file") as from_file:
        spec = YamlFileSpec(filename=filename)
        spec.environment
    from_file.assert_called_with(filename)


def test_yaml_file_import():
    deprecated = importlib.import_module("conda_env.specs.yaml_file")
    redirect_module = importlib.import_module("conda.env.specs.yaml_file")

    assert getattr(deprecated, "YamlFileSpec") is getattr(
        redirect_module, "YamlFileSpec"
    )
