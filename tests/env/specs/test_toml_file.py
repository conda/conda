# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
from os import path

from pytest import mark

from conda.env.specs.toml_file import TomlSpec

from .. import support_file

# samples that should be handles
_real_samples_handleable = [
    "django-pass.toml",
    "numpy-pass.toml",
    "pylint-pass.toml",
    "flask-pass.toml",
]

# samples that con not be handled
_real_samples_unhandleable = [
    "django-fail.toml",
    "numpy-fail.toml",
    "pylint-fail.toml",
    "flask-fail.toml",
]


# all test cases are inside `env-toml` directory
def _support_file(filename):
    filename = path.join("env-toml", filename)
    return support_file(filename)


def test_no_environment_file():
    spec = TomlSpec(name="mock", filename="not-a-file")
    assert not spec.can_handle()


def test_enviroment_file_not_a_toml():
    spec = TomlSpec(name="mock", filename=_support_file("not_a_toml.txt"))
    assert not spec.can_handle(), spec.msg


def test_environment_file_without_name():
    """either .toml file has a name, or it's provided as an argument"""
    spec = TomlSpec(name=None, filename=_support_file("mock_proj_no_name.toml"))
    assert not spec.can_handle(), spec.msg
    spec = TomlSpec(name="mock", filename=_support_file("mock_proj_no_name.toml"))
    assert spec.can_handle(), spec.msg


@mark.parametrize("filename", _real_samples_unhandleable)
def test_read_world_examples_unhandleable(filename):
    """Shoud fail to handle real-world examples as they don't have `channels=[]`"""
    spec = TomlSpec(name=None, filename=_support_file(filename))
    assert not spec.can_handle(), spec.msg


@mark.parametrize("filename", _real_samples_handleable)
def test_read_world_examples_handleable(filename):
    """Shoud fail to handle real-world examples as they don't have `channels=[]`"""
    spec = TomlSpec(name=None, filename=_support_file(filename))
    assert spec.can_handle(), spec.msg


# TODO: intergration test to check if installation can actually be done
# There are some grammarly correct files (e.g. `mock_proj_invalid_dep_version.toml`)
# that could pass the above test, but would fail to install (invalid version, etc.)
