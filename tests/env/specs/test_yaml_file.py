# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
from unittest import mock

from conda.env import env
from conda.env.specs.yaml_file import YamlFileSpec

from .. import support_file


def test_no_environment_file():
    spec = YamlFileSpec(name=None, filename="not-a-file")
    assert not spec.can_handle()


def test_environment_file_exist():
    spec = YamlFileSpec(name=None, filename=support_file("simple.yml"))
    assert spec.can_handle()


def test_environment_file_not_yaml():
    spec = YamlFileSpec(name=None, filename=support_file("requirements.txt"))
    assert not spec.can_handle()


def test_get_environment():
    spec = YamlFileSpec(name=None, filename=support_file("simple.yml"))
    assert spec.env is not None


def test_filename():
    filename = support_file("simple.yml")
    with mock.patch.object(env, "from_file") as from_file:
        spec = YamlFileSpec(filename=filename)
        spec.env
    from_file.assert_called_with(filename)
