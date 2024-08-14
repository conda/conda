# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause

from conda.models.environment import Environment


def test_environment():
    env = Environment(name="test")
    assert env.name == "test"
