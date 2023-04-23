# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
import sys
from argparse import ArgumentParser, _StoreTrueAction

import pytest

from conda.deprecations import DeprecatedError, DeprecationHandler


@pytest.fixture(scope="module")
def deprecated_v1() -> DeprecationHandler:
    return DeprecationHandler("1.0")


@pytest.fixture(scope="module")
def deprecated_v2() -> DeprecationHandler:
    return DeprecationHandler("2.0")


@pytest.fixture(scope="module")
def deprecated_v3() -> DeprecationHandler:
    return DeprecationHandler("3.0")


def test_function_pending(deprecated_v1: DeprecationHandler):
    @deprecated_v1("2.0", "3.0")
    def foo():
        return True

    # alerting user that a function will be unavailable
    with pytest.deprecated_call(match="pending deprecation"):
        assert foo()


def test_function_deprecated(deprecated_v2: DeprecationHandler):
    @deprecated_v2("2.0", "3.0")
    def foo():
        return True

    # alerting user that a function will be unavailable
    with pytest.deprecated_call(match="deprecated"):
        assert foo()


def test_function_remove(deprecated_v3: DeprecationHandler):
    # alerting developer that a function needs to be removed
    with pytest.raises(DeprecatedError):

        @deprecated_v3("2.0", "3.0")
        def foo():
            return True


def test_method_pending(deprecated_v1: DeprecationHandler):
    class Bar:
        @deprecated_v1("2.0", "3.0")
        def foo(self):
            return True

    with pytest.deprecated_call(match="pending deprecation"):
        assert Bar().foo()


def test_method_deprecated(deprecated_v2: DeprecationHandler):
    class Bar:
        @deprecated_v2("2.0", "3.0")
        def foo(self):
            return True

    with pytest.deprecated_call(match="deprecated"):
        assert Bar().foo()


def test_method_remove(deprecated_v3: DeprecationHandler):
    with pytest.raises(DeprecatedError):

        class Bar:
            @deprecated_v3("2.0", "3.0")
            def foo(self):
                return True


def test_class_pending(deprecated_v1: DeprecationHandler):
    @deprecated_v1("2.0", "3.0")
    class Foo:
        pass

    with pytest.deprecated_call(match="pending deprecation"):
        assert Foo()


def test_class_deprecated(deprecated_v2: DeprecationHandler):
    @deprecated_v2("2.0", "3.0")
    class Foo:
        pass

    with pytest.deprecated_call(match="deprecated"):
        assert Foo()


def test_class_remove(deprecated_v3: DeprecationHandler):
    with pytest.raises(DeprecatedError):

        @deprecated_v3("2.0", "3.0")
        class Foo:
            pass


def test_arguments_pending(deprecated_v1: DeprecationHandler):
    @deprecated_v1.argument("2.0", "3.0", "three")
    def foo(one, two):
        return True

    # too many arguments, can only deprecate keyword arguments
    with pytest.raises(TypeError):
        assert foo(1, 2, 3)

    # alerting user to pending deprecation
    with pytest.deprecated_call(match="pending deprecation"):
        assert foo(1, 2, three=3)

    # normal usage not needing deprecation
    assert foo(1, 2)


def test_arguments_deprecated(deprecated_v2: DeprecationHandler):
    @deprecated_v2.argument("2.0", "3.0", "three")
    def foo(one, two):
        return True

    # too many arguments, can only deprecate keyword arguments
    with pytest.raises(TypeError):
        assert foo(1, 2, 3)

    # alerting user to pending deprecation
    with pytest.deprecated_call(match="deprecated"):
        assert foo(1, 2, three=3)

    # normal usage not needing deprecation
    assert foo(1, 2)


def test_arguments_remove(deprecated_v3: DeprecationHandler):
    # alerting developer that a keyword argument needs to be removed
    with pytest.raises(DeprecatedError):

        @deprecated_v3.argument("2.0", "3.0", "three")
        def foo(one, two):
            return True


def test_action_pending(deprecated_v1: DeprecationHandler):
    parser = ArgumentParser()
    parser.add_argument(
        "--foo",
        action=deprecated_v1.action("2.0", "3.0", _StoreTrueAction),
    )

    with pytest.deprecated_call(match="pending deprecation"):
        parser.parse_args(["--foo"])


def test_action_deprecated(deprecated_v2: DeprecationHandler):
    parser = ArgumentParser()
    parser.add_argument(
        "--foo",
        action=deprecated_v2.action("2.0", "3.0", _StoreTrueAction),
    )

    with pytest.deprecated_call(match="deprecated"):
        parser.parse_args(["--foo"])


def test_action_remove(deprecated_v3: DeprecationHandler):
    parser = ArgumentParser()

    with pytest.raises(DeprecatedError):
        parser.add_argument(
            "--foo",
            action=deprecated_v3.action("2.0", "3.0", _StoreTrueAction),
        )


def test_module_pending(deprecated_v1: DeprecationHandler):
    # alerting user to pending deprecation
    with pytest.deprecated_call(match="pending deprecation"):
        deprecated_v1.module("2.0", "3.0")


def test_module_deprecated(deprecated_v2: DeprecationHandler):
    # alerting user to pending deprecation
    with pytest.deprecated_call(match="deprecated"):
        deprecated_v2.module("2.0", "3.0")


def test_module_remove(deprecated_v3: DeprecationHandler):
    # alerting developer that a module needs to be removed
    with pytest.raises(DeprecatedError):
        deprecated_v3.module("2.0", "3.0")


def test_constant_pending(deprecated_v1: DeprecationHandler):
    deprecated_v1.constant("2.0", "3.0", "SOME_CONSTANT", 42)
    module = sys.modules[__name__]

    # alerting user to pending deprecation
    with pytest.deprecated_call(match="pending deprecation"):
        module.SOME_CONSTANT


def test_constant_deprecated(deprecated_v2: DeprecationHandler):
    deprecated_v2.constant("2.0", "3.0", "SOME_CONSTANT", 42)
    module = sys.modules[__name__]

    # alerting user to pending deprecation
    with pytest.deprecated_call(match="deprecated"):
        module.SOME_CONSTANT


def test_constant_remove(deprecated_v3: DeprecationHandler):
    # alerting developer that a module needs to be removed
    with pytest.raises(DeprecatedError):
        deprecated_v3.constant("2.0", "3.0", "SOME_CONSTANT", 42)


def test_topic_pending(deprecated_v1: DeprecationHandler):
    # alerting user to pending deprecation
    with pytest.deprecated_call(match="pending deprecation"):
        deprecated_v1.topic("2.0", "3.0", topic="Some special topic")


def test_topic_deprecated(deprecated_v2: DeprecationHandler):
    # alerting user to pending deprecation
    with pytest.deprecated_call(match="deprecated"):
        deprecated_v2.topic("2.0", "3.0", topic="Some special topic")


def test_topic_remove(deprecated_v3: DeprecationHandler):
    # alerting developer that a module needs to be removed
    with pytest.raises(DeprecatedError):
        deprecated_v3.topic("2.0", "3.0", topic="Some special topic")


def test_version_fallback():
    """
    Test that conda can run even if deprecations can't parse the version.
    """
    version = DeprecationHandler(None)._version  # type: ignore
    assert version.major == version.minor == version.micro == 0
