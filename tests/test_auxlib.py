# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
import pytest

from conda.auxlib.decorators import classproperty


def test_deprecations():
    with pytest.deprecated_call():

        class Foo:
            @classproperty
            def bar(cls):
                return 42

    assert Foo.bar == 42
