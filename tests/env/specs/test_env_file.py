# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
import random
from unittest import mock

from conda.env import env
from conda.env.specs.env_file import EnvironmentFileSpec


def test_no_environment_file():
    spec = EnvironmentFileSpec(name=None, filename="not-a-file")
    assert not spec.can_handle()


def test_environment_file_exist():
    with mock.patch.object(env, "from_file", return_value={}):
        spec = EnvironmentFileSpec(name=None, filename="environment.yaml")
        assert spec.can_handle()


def test_get_environment():
    r = random.randint(100, 200)
    with mock.patch.object(env, "from_file", return_value=r):
        spec = EnvironmentFileSpec(name=None, filename="environment.yaml")
        assert spec.environment == r


def test_filename():
    filename = f"filename_{random.randint(100, 200)}"
    with mock.patch.object(env, "from_file") as from_file:
        spec = EnvironmentFileSpec(filename=filename)
        spec.environment
    from_file.assert_called_with(filename)
