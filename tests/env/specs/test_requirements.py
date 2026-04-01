# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
import pytest

from conda.env.specs.requirements import RequirementsSpec
from conda.exceptions import CondaValueError, PluginError
from conda.models.environment import Environment

from .. import support_file


def test_no_environment_file():
    spec = RequirementsSpec(filename="not-a-file")
    with pytest.raises(CondaValueError):
        spec.can_handle()


def test_no_name():
    spec = RequirementsSpec(filename=support_file("requirements.txt"))
    assert spec.can_handle()


def test_req_file_and_name():
    spec = RequirementsSpec(filename=support_file("requirements.txt"))
    assert spec.can_handle()


def test_can_not_handle_explicit():
    spec = RequirementsSpec(filename=support_file("explicit.txt"))
    with pytest.raises(PluginError):
        spec.can_handle()


def test_environment():
    spec = RequirementsSpec(filename=support_file("requirements.txt"))
    assert isinstance(spec.env, Environment)
    assert spec.env.requested_packages[0].name == "conda-package-handling"
