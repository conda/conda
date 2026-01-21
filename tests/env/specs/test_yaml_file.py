# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
from unittest import mock

from conda.env import env
from conda.env.specs.yaml_file import YamlFileSpec

from .. import support_file


def test_environment_file_exist():
    spec = YamlFileSpec(filename=support_file("simple.yml"))
    assert spec.can_handle()


def test_environment_file_not_yaml():
    spec = YamlFileSpec(filename=support_file("requirements.txt"))
    assert not spec.can_handle()


def test_get_environment():
    spec = YamlFileSpec(filename=support_file("simple.yml"))
    assert spec.env is not None


def test_filename():
    filename = support_file("simple.yml")
    spec = YamlFileSpec(filename=filename)
    env = spec.env
    assert "nltk" in [spec.name for spec in env.requested_packages]
    assert env.name == "nlp"
