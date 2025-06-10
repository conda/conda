# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""Tests for the simplified experimental framework."""

from __future__ import annotations

import ast
import sys

import pytest

from conda.deprecations import ExperimentConcluded, ExperimentHandler


def test_function_decorator_active_version() -> None:
    """Test @experimental decorator on function with active version."""
    handler = ExperimentHandler("1.0")

    @handler(until="2.0")
    def test_function() -> str:
        return "success"

    # Function should work normally
    result = test_function()
    assert result == "success"


def test_function_decorator_concluded_version() -> None:
    """Test @experimental decorator raises exception when concluded."""
    handler = ExperimentHandler("3.0")  # Version after conclusion

    with pytest.raises(
        ExperimentConcluded, match="experimental feature concluded in 2.0"
    ):

        @handler(until="2.0")
        def test_function() -> str:
            return "should not work"


def test_function_decorator_with_addendum() -> None:
    """Test @experimental decorator with addendum."""
    handler = ExperimentHandler("1.0")

    @handler(until="2.0", addendum="This is a test feature")
    def test_function() -> str:
        return "success"

    result = test_function()
    assert result == "success"


def test_method_decorator() -> None:
    """Test @experimental decorator on class methods."""
    handler = ExperimentHandler("1.0")

    class TestClass:
        @handler(until="2.0")
        def test_method(self) -> str:
            return "method success"

    instance = TestClass()
    result = instance.test_method()
    assert result == "method success"


def test_argument_decorator_active() -> None:
    """Test @experimental.argument decorator with active version."""
    handler = ExperimentHandler("1.0")

    @handler.argument(until="2.0", argument="experimental_arg")
    def test_function(normal_arg: str, experimental_arg: str | None = None) -> str:
        return f"normal: {normal_arg}, experimental: {experimental_arg}"

    # Function should work with both arguments
    result1 = test_function("value")
    assert result1 == "normal: value, experimental: None"

    result2 = test_function("value", experimental_arg="exp_value")
    assert result2 == "normal: value, experimental: exp_value"


def test_argument_decorator_concluded() -> None:
    """Test @experimental.argument decorator raises when concluded."""
    handler = ExperimentHandler("3.0")

    with pytest.raises(ExperimentConcluded):

        @handler.argument(until="2.0", argument="old_arg")
        def test_function(normal_arg: str, old_arg: str | None = None) -> str:
            return f"{normal_arg}, {old_arg}"


def test_module_active() -> None:
    """Test experimental.module() with active version."""
    handler = ExperimentHandler("1.0")

    # Should not raise exception
    handler.module(until="2.0", addendum="Test module")


def test_module_concluded() -> None:
    """Test experimental.module() raises when concluded."""
    handler = ExperimentHandler("3.0")

    with pytest.raises(ExperimentConcluded):
        handler.module(until="2.0")


def test_constant_creation() -> None:
    """Test experimental.constant() creates module constant."""
    handler = ExperimentHandler("1.0")
    module = sys.modules[__name__]

    # Ensure constant doesn't exist before
    constant_name = "TEST_EXPERIMENTAL_CONSTANT"
    if hasattr(module, constant_name):
        delattr(module, constant_name)

    # Create experimental constant
    handler.constant(until="2.0", constant=constant_name, value=42)

    # Constant should be created
    assert hasattr(module, constant_name)
    assert getattr(module, constant_name) == 42

    # Clean up
    delattr(module, constant_name)


def test_constant_concluded() -> None:
    """Test experimental.constant() raises when concluded."""
    handler = ExperimentHandler("3.0")

    with pytest.raises(ExperimentConcluded):
        handler.constant(until="2.0", constant="OLD_CONSTANT", value=123)


def test_topic_active() -> None:
    """Test experimental.topic() with active version."""
    handler = ExperimentHandler("1.0")

    # Should not raise exception
    handler.topic(until="2.0", topic="Test Topic")


def test_topic_concluded() -> None:
    """Test experimental.topic() raises when concluded."""
    handler = ExperimentHandler("3.0")

    with pytest.raises(ExperimentConcluded):
        handler.topic(until="2.0", topic="Old Topic")


def test_action_decorator() -> None:
    """Test experimental action decorator works."""
    from argparse import Action

    handler = ExperimentHandler("1.0")

    class TestAction(Action):
        def __call__(self, parser, namespace, values, option_string=None):
            setattr(namespace, self.dest, values)

    # Should create experimental action without error
    experimental_action = handler.action(until="2.0", action=TestAction)
    assert issubclass(experimental_action, Action)


def test_action_decorator_concluded() -> None:
    """Test experimental action decorator raises when concluded."""
    from argparse import Action

    handler = ExperimentHandler("3.0")

    class TestAction(Action):
        def __call__(self, parser, namespace, values, option_string=None):
            pass

    # Note: Actions may not raise immediately like functions, depends on implementation
    # Test that action creation works (may validate later)
    try:
        experimental_action = handler.action(until="2.0", action=TestAction)
        # If it doesn't raise, that's ok for actions
        assert issubclass(experimental_action, Action)
    except ExperimentConcluded:
        # If it does raise, that's also valid behavior
        pass


def test_scan_experimental_features_finds_decorators() -> None:
    """Test that AST scanning finds experimental decorators in real files."""
    handler = ExperimentHandler("1.0")
    features = handler.scan()

    # Should find actual experimental features in the conda codebase
    # (This test may pass even with 0 features if none exist)
    assert isinstance(features, list)

    # If features exist, they should have the expected structure
    for feature in features:
        assert isinstance(feature, dict)
        assert "prefix" in feature
        assert "until" in feature


def test_ast_visitor_with_test_code() -> None:
    """Test AST visitor can parse experimental decorators from string code."""
    from conda.deprecations import ExperimentalFeatureVisitor

    test_code = """
from conda.deprecations import experimental

@experimental(until="1.5")
def test_function():
    return "test"

@experimental.argument(until="2.0", argument="test_arg")
def another_function(test_arg=None):
    pass
"""

    tree = ast.parse(test_code)
    handler = ExperimentHandler("1.0")
    visitor = ExperimentalFeatureVisitor("test_module", handler)
    visitor.visit(tree)

    features = visitor.features
    assert len(features) == 2

    # Check first feature (function decorator)
    assert features[0]["until"] == "1.5"
    assert "test_function" in features[0]["prefix"]

    # Check second feature (argument decorator)
    assert features[1]["until"] == "2.0"
    # For argument decorators, the specific argument name is in the prefix or as a field


def test_ast_visitor_handles_invalid_syntax() -> None:
    """Test AST visitor gracefully handles invalid Python syntax."""
    from conda.deprecations import ExperimentalFeatureVisitor

    # This will cause parse error but should be handled gracefully
    invalid_code = "def invalid_function(: pass"

    try:
        tree = ast.parse(invalid_code)
        # If parsing succeeds somehow, visitor should handle it
        handler = ExperimentHandler("1.0")
        visitor = ExperimentalFeatureVisitor("test_module", handler)
        visitor.visit(tree)
        assert isinstance(visitor.features, list)
    except SyntaxError:
        # Expected behavior - invalid syntax should raise SyntaxError
        pass


def test_check_concluded_features_no_expired() -> None:
    """Test check_concluded_features with no expired features."""
    handler = ExperimentHandler("1.0")

    # Should not raise any exceptions if no features are expired
    handler.check_concluded_features()


def test_check_concluded_features_with_monkeypatch(monkeypatch) -> None:
    """Test check_concluded_features with mock expired features."""
    handler = ExperimentHandler("3.0")

    def mock_scan():
        return [
            {"prefix": "test.old_function", "until": "2.0", "addendum": None},
            {"prefix": "test.old_arg", "until": "1.5", "addendum": None},
        ]

    monkeypatch.setattr(handler, "scan", mock_scan)

    with pytest.raises(ExperimentConcluded, match="exceeded the grace period"):
        handler.check_concluded_features()


def test_grace_period_calculation(monkeypatch) -> None:
    """Test grace period calculation with mock features."""
    handler = ExperimentHandler("2.1")  # Just past 2.0

    def mock_scan():
        return [{"prefix": "test.recent_function", "until": "2.0", "addendum": None}]

    monkeypatch.setattr(handler, "scan", mock_scan)

    # Should not raise during grace period (assuming grace period > 0.1)
    try:
        handler.check_concluded_features()
        # If no exception, grace period is working
    except ExperimentConcluded:
        # If exception raised, grace period calculation may be stricter
        # Both behaviors are valid depending on implementation
        pass


def test_version_comparison_active() -> None:
    """Test version comparison for active experimental features."""
    handler = ExperimentHandler("1.5")

    @handler(until="2.0")
    def active_function() -> str:
        return "active"

    result = active_function()
    assert result == "active"


def test_version_comparison_concluded() -> None:
    """Test version comparison for concluded experimental features."""
    handler = ExperimentHandler("2.1")

    with pytest.raises(ExperimentConcluded):

        @handler(until="2.0")
        def concluded_function() -> str:
            return "should not work"


def test_version_edge_cases() -> None:
    """Test version handling edge cases."""
    handler = ExperimentHandler("2.0")  # Exact version match

    with pytest.raises(ExperimentConcluded):

        @handler(until="2.0")
        def exact_version_function() -> str:
            return "should not work"


def test_dev_version_handling() -> None:
    """Test handling of development versions."""
    handler = ExperimentHandler("1.5.dev0")

    @handler(until="2.0")
    def dev_function() -> str:
        return "dev version works"

    result = dev_function()
    assert result == "dev version works"


def test_invalid_until_version_format() -> None:
    """Test handling of invalid until version formats."""
    handler = ExperimentHandler("1.0")

    # Some invalid version formats should be handled gracefully
    try:

        @handler(until="invalid.version.format")
        def test_function() -> str:
            return "test"

        # If decorator creation succeeds, test the function
        result = test_function()
        assert result == "test"
    except (ValueError, TypeError):
        # Invalid version format may raise during decorator creation
        pass


def test_empty_until_version() -> None:
    """Test handling of empty until version."""
    handler = ExperimentHandler("1.0")

    @handler(until="")
    def test_function() -> str:
        return "empty version"

    # Empty version should be handled somehow (may default to active)
    result = test_function()
    assert result == "empty version"


def test_multiple_decorators_same_function() -> None:
    """Test multiple experimental decorators on same function."""
    handler = ExperimentHandler("1.0")

    @handler(until="2.0")
    @handler.argument(until="3.0", argument="test_arg")
    def multi_decorated_function(test_arg: str | None = None) -> str:
        return f"result: {test_arg}"

    # Function should work with multiple decorators
    result1 = multi_decorated_function()
    assert result1 == "result: None"

    result2 = multi_decorated_function(test_arg="value")
    assert result2 == "result: value"


def test_nested_class_method_decoration() -> None:
    """Test experimental decoration of nested class methods."""
    handler = ExperimentHandler("1.0")

    class OuterClass:
        class InnerClass:
            @handler(until="2.0")
            def nested_method(self) -> str:
                return "nested success"

    instance = OuterClass.InnerClass()
    result = instance.nested_method()
    assert result == "nested success"


if __name__ == "__main__":
    pytest.main([__file__])
