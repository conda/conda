# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
from conda import _deprecated

import pytest


def test_pending():
    @_deprecated(deprecate_in="2.0", remove_in="3.0", _current="1.0")
    def foo():
        return True

    with pytest.deprecated_call():
        assert foo()


def test_deprecated():
    @_deprecated(deprecate_in="2.0", remove_in="3.0", _current="2.0")
    def foo():
        return True

    with pytest.deprecated_call():
        assert foo()


def test_remove():
    with pytest.raises(RuntimeError):

        @_deprecated(deprecate_in="2.0", remove_in="3.0", _current="3.0")
        def foo():
            return True


def test_module_pending():
    with pytest.deprecated_call():
        _deprecated.module(deprecate_in="2.0", remove_in="3.0", _current="1.0")


def test_module_deprecated():
    with pytest.deprecated_call():
        _deprecated.module(deprecate_in="2.0", remove_in="3.0", _current="2.0")


def test_module_remove():
    with pytest.raises(RuntimeError):
        _deprecated.module(deprecate_in="2.0", remove_in="3.0", _current="3.0")
