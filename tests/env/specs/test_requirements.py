# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause

from conda.env.specs.requirements import RequirementsSpec
from conda.models.environment import Environment

from .. import support_file


def test_no_environment_file():
    spec = RequirementsSpec(name=None, filename="not-a-file")
    assert not spec.can_handle()


def test_no_name():
    spec = RequirementsSpec(filename=support_file("requirements.txt"))
    assert spec.can_handle()
    assert spec.name is None  # this is caught in the application layer


def test_req_file_and_name():
    spec = RequirementsSpec(filename=support_file("requirements.txt"), name="env")
    assert spec.can_handle()


def test_can_not_handle_explicit():
    spec = RequirementsSpec(filename=support_file("explicit.txt"))
    assert not spec.can_handle()


def test_environment():
    spec = RequirementsSpec(filename=support_file("requirements.txt"), name="env")
    assert isinstance(spec.env, Environment)
    pkg = spec.env.requested_packages[0]
    assert pkg.name == "conda-package-handling"
    assert pkg.version == "2.2.0"
