# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause

import pytest

from conda.env.env import Environment
from conda.env.specs.requirements import RequirementsSpec

from .. import support_file


def test_no_environment_file():
    with pytest.deprecated_call():
        spec = RequirementsSpec(name=None, filename="not-a-file")
        assert not spec.can_handle()


def test_no_name():
    with pytest.deprecated_call():
        spec = RequirementsSpec(filename=support_file("requirements.txt"))
        assert spec.can_handle()
        assert spec.name is None  # this is caught in the application layer


def test_req_file_and_name():
    with pytest.deprecated_call():
        spec = RequirementsSpec(filename=support_file("requirements.txt"), name="env")
        assert spec.can_handle()


def test_can_not_handle_explicit():
    spec = RequirementsSpec(filename=support_file("explicit.txt"))
    assert not spec.can_handle()


def test_environment():
    with pytest.deprecated_call():
        spec = RequirementsSpec(filename=support_file("requirements.txt"), name="env")
        assert isinstance(spec.environment, Environment)
        assert (
            spec.environment.dependencies["conda"][0] == "conda-package-handling==2.2.0"
        )
