# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause

from conda.env.env import Environment
from conda.env.specs.requirements import RequirementsSpec

from .. import support_file


def test_no_environment_file():
    spec = RequirementsSpec(name=None, filename="not-a-file")
    assert not spec.validate_source_name()


def test_no_name():
    spec = RequirementsSpec(filename=support_file("requirements.txt"))
    assert spec.validate_source_name()
    assert spec.validate_schema()
    assert spec.name is None  # this is caught in the application layer


def test_req_file_and_name():
    spec = RequirementsSpec(filename=support_file("requirements.txt"), name="env")
    assert spec.validate_source_name()
    assert spec.validate_schema()


def test_environment():
    spec = RequirementsSpec(filename=support_file("requirements.txt"), name="env")
    assert isinstance(spec.environment, Environment)
    assert spec.environment.dependencies["conda"][0] == "conda-package-handling==2.2.0"
