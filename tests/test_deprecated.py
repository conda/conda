# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
from conda import _deprecated_factory

import pytest


@pytest.fixture(scope="module")
def deprecated_1():
    return _deprecated_factory("1.0")


@pytest.fixture(scope="module")
def deprecated_2():
    return _deprecated_factory("2.0")


@pytest.fixture(scope="module")
def deprecated_3():
    return _deprecated_factory("3.0")


def test_pending(deprecated_1):
    @deprecated_1(deprecate_in="2.0", remove_in="3.0")
    def foo():
        return True

    with pytest.deprecated_call():
        assert foo()


def test_deprecated(deprecated_2):
    @deprecated_2(deprecate_in="2.0", remove_in="3.0")
    def foo():
        return True

    with pytest.deprecated_call():
        assert foo()


def test_remove(deprecated_3):
    with pytest.raises(RuntimeError):

        @deprecated_3(deprecate_in="2.0", remove_in="3.0")
        def foo():
            return True


def test_module_pending(deprecated_1):
    with pytest.deprecated_call():
        deprecated_1.module(deprecate_in="2.0", remove_in="3.0")


def test_module_deprecated(deprecated_2):
    with pytest.deprecated_call():
        deprecated_2.module(deprecate_in="2.0", remove_in="3.0")


def test_module_remove(deprecated_3):
    with pytest.raises(RuntimeError):
        deprecated_3.module(deprecate_in="2.0", remove_in="3.0")
