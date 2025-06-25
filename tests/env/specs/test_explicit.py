# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause

from conda.env.env import Environment
from conda.env.specs.explicit import ExplicitSpec

from .. import support_file


def test_no_environment_file():
    spec = ExplicitSpec()
    assert not spec.can_handle()


def test_can_handle_explicit():
    spec = ExplicitSpec(filename=support_file("explicit.txt"))
    assert spec.can_handle()


def test_can_not_handle_requirements_txt():
    spec = ExplicitSpec(filename=support_file("requirements.txt"))
    assert not spec.can_handle()


def test_environment():
    spec = ExplicitSpec(filename=support_file("explicit.txt"))
    assert isinstance(spec.environment, Environment)
    assert spec.environment.dependencies.explicit is True
    assert "defaults/linux-64::python==3.9.0=h8bdb77d_3"  in spec.environment.dependencies["conda"]
