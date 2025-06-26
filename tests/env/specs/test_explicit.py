# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause

from conda.env.specs.explicit import ExplicitSpec
from conda.models.environment import Environment

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
    assert len(spec.environment.explicit_packages) > 0
    assert "ca-certificates" in [pkg.name for pkg in spec.environment.explicit_packages]
