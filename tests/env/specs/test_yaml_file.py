# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
from unittest import mock

import pytest

from conda.env import env
from conda.env.specs.cep_24 import Cep24YamlFileSpec
from conda.env.specs.yaml_file import YamlFileSpec
from conda.exceptions import EnvironmentFileNotFound, PluginError

from .. import support_file


@pytest.mark.parametrize(
    "cls",
    [
        YamlFileSpec,
        Cep24YamlFileSpec,
    ],
)
def test_no_environment_file(cls):
    spec = cls(name=None, filename="not-a-file")
    with pytest.raises(EnvironmentFileNotFound):
        spec.can_handle()


@pytest.mark.parametrize("cls", [YamlFileSpec, Cep24YamlFileSpec])
def test_environment_file_exist(cls):
    spec = cls(name=None, filename=support_file("simple.yml"))
    assert spec.can_handle()


@pytest.mark.parametrize(
    "cls,err",
    [
        (YamlFileSpec, PluginError),
        (Cep24YamlFileSpec, TypeError),
    ],
)
def test_environment_file_not_yaml(cls, err):
    spec = cls(name=None, filename=support_file("requirements.txt"))
    with pytest.raises(err):
        spec.can_handle()


@pytest.mark.parametrize("cls", [YamlFileSpec, Cep24YamlFileSpec])
def test_get_environment(cls):
    spec = cls(name=None, filename=support_file("simple.yml"))
    assert spec.env is not None


def test_filename():
    filename = support_file("simple.yml")
    with mock.patch.object(env, "from_file") as from_file:
        spec = YamlFileSpec(filename=filename)
        spec.env
    from_file.assert_called_with(filename)
