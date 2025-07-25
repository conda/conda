# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""Tests for conda.cli.helpers module."""

from __future__ import annotations

import argparse
from argparse import ArgumentParser, Namespace

import pytest

from conda.cli.helpers import LazyChoicesAction


@pytest.fixture
def simple_choices():
    """Fixture providing simple test choices."""
    return ["red", "green", "blue"]


@pytest.fixture
def export_format_choices():
    """Fixture providing realistic export format choices."""
    return ["environment-json", "environment-yaml", "explicit", "json", "yaml"]


@pytest.fixture
def solver_choices():
    """Fixture providing realistic solver choices."""
    return ["classic", "libmamba"]


@pytest.fixture
def choices_func_counter():
    """Fixture providing a choices function that counts calls."""
    call_count = {"count": 0}

    def func():
        call_count["count"] += 1
        return ["option1", "option2", "option3"]

    func.call_count = lambda: call_count["count"]
    return func


@pytest.fixture
def lazy_action(simple_choices):
    """Fixture providing a basic LazyChoicesAction."""
    return LazyChoicesAction(
        option_strings=["--test"],
        dest="test",
        choices_func=lambda: simple_choices,
    )


@pytest.fixture
def mock_parser_namespace():
    """Fixture providing mock parser and namespace objects."""

    class MockParser:
        def __init__(self):
            self.error_called = False
            self.error_message = None

        def error(self, message):
            self.error_called = True
            self.error_message = message

    parser = MockParser()
    namespace = Namespace()
    return parser, namespace


def test_lazy_choices_action_initialization(simple_choices):
    """Test basic initialization of LazyChoicesAction."""
    choices_func = lambda: simple_choices
    action = LazyChoicesAction(
        option_strings=["--test"],
        dest="test",
        choices_func=choices_func,
    )
    assert action.choices_func == choices_func
    assert action.dest == "test"


def test_choices_property_evaluation(choices_func_counter):
    """Test that choices property dynamically evaluates choices_func."""
    action = LazyChoicesAction(
        option_strings=["--test"],
        dest="test",
        choices_func=choices_func_counter,
    )

    # First access
    choices1 = action.choices
    assert choices1 == ["option1", "option2", "option3"]
    assert choices_func_counter.call_count() == 1

    # Second access - should call function again (no caching)
    choices2 = action.choices
    assert choices2 == ["option1", "option2", "option3"]
    assert choices_func_counter.call_count() == 2


def test_choices_setter_ignores_values():
    """Test that choices setter ignores attempts to set static choices."""
    choices_func = lambda: ["dynamic1", "dynamic2"]
    action = LazyChoicesAction(
        option_strings=["--test"],
        dest="test",
        choices_func=choices_func,
    )

    # Try to set choices (this happens during argparse init)
    action.choices = ["static1", "static2"]

    # Should still return dynamic choices
    assert action.choices == ["dynamic1", "dynamic2"]


def test_valid_choice_handling(lazy_action, mock_parser_namespace):
    """Test action call with valid choice."""
    parser, namespace = mock_parser_namespace

    # Valid choice should set attribute without error
    lazy_action(parser, namespace, "red", "--test")
    assert namespace.test == "red"
    assert not parser.error_called


def test_invalid_choice_handling(lazy_action, mock_parser_namespace):
    """Test action call with invalid choice raises error."""
    parser, namespace = mock_parser_namespace

    # Invalid choice should call parser.error
    lazy_action(parser, namespace, "purple", "--test")
    assert parser.error_called
    assert "invalid choice: 'purple'" in parser.error_message
    assert "choose from 'red', 'green', 'blue'" in parser.error_message


def test_argumentparser_help_integration(export_format_choices):
    """Test that LazyChoicesAction works with ArgumentParser help generation."""
    parser = ArgumentParser(prog="test")
    parser.add_argument(
        "--format",
        action=LazyChoicesAction,
        choices_func=lambda: export_format_choices,
        help="Choose a format",
    )

    # Get help text
    help_output = parser.format_help()

    # Should show choices in help
    assert "{environment-json,environment-yaml,explicit,json,yaml}" in help_output
    assert "Choose a format" in help_output


def test_argumentparser_error_handling():
    """Test that LazyChoicesAction error handling works with ArgumentParser."""
    choices_func = lambda: ["alpha", "beta", "gamma"]

    parser = ArgumentParser(prog="test")
    parser.add_argument(
        "--choice",
        action=LazyChoicesAction,
        choices_func=choices_func,
    )

    # Should raise SystemExit for invalid choice
    with pytest.raises((SystemExit, argparse.ArgumentError)):
        parser.parse_args(["--choice", "invalid"])


def test_argumentparser_valid_parsing():
    """Test that LazyChoicesAction works correctly with valid parsing."""
    choices_func = lambda: ["one", "two", "three"]

    parser = ArgumentParser(prog="test")
    parser.add_argument(
        "--number",
        action=LazyChoicesAction,
        choices_func=choices_func,
    )

    # Valid choice should parse correctly
    args = parser.parse_args(["--number", "two"])
    assert args.number == "two"


def test_choices_func_exception_propagation():
    """Test that exceptions in choices_func are propagated."""

    def failing_choices_func():
        raise ValueError("Choices function failed")

    action = LazyChoicesAction(
        option_strings=["--test"],
        dest="test",
        choices_func=failing_choices_func,
    )

    # Exception should be propagated when accessing choices
    with pytest.raises(ValueError, match="Choices function failed"):
        _ = action.choices


def test_empty_choices_behavior(mock_parser_namespace):
    """Test behavior with empty choices list."""
    action = LazyChoicesAction(
        option_strings=["--test"],
        dest="test",
        choices_func=lambda: [],
    )

    parser, namespace = mock_parser_namespace

    # Any value should be invalid with empty choices
    action(parser, namespace, "anything", "--test")
    assert parser.error_called
    assert "invalid choice: 'anything'" in parser.error_message


def test_non_list_iterable_choices(mock_parser_namespace):
    """Test that choices_func can return any iterable."""
    action = LazyChoicesAction(
        option_strings=["--test"],
        dest="test",
        choices_func=lambda: {"set", "of", "choices"},  # set instead of list
    )

    parser, namespace = mock_parser_namespace

    # Valid choice from set should work
    action(parser, namespace, "set", "--test")
    assert namespace.test == "set"
    assert not parser.error_called


@pytest.mark.parametrize("valid_choice", ["yaml", "json", "explicit"])
def test_parametrized_valid_choices(valid_choice, mock_parser_namespace):
    """Test multiple valid choices using parametrization."""
    action = LazyChoicesAction(
        option_strings=["--format"],
        dest="format",
        choices_func=lambda: ["yaml", "json", "explicit"],
    )

    parser, namespace = mock_parser_namespace

    action(parser, namespace, valid_choice, "--format")
    assert getattr(namespace, "format") == valid_choice
    assert not parser.error_called


@pytest.mark.parametrize("invalid_choice", ["xml", "csv", "invalid"])
def test_parametrized_invalid_choices(invalid_choice, mock_parser_namespace):
    """Test multiple invalid choices using parametrization."""
    action = LazyChoicesAction(
        option_strings=["--format"],
        dest="format",
        choices_func=lambda: ["yaml", "json", "explicit"],
    )

    parser, namespace = mock_parser_namespace

    action(parser, namespace, invalid_choice, "--format")
    assert parser.error_called
    assert f"invalid choice: '{invalid_choice}'" in parser.error_message


def test_multiple_option_strings(mock_parser_namespace):
    """Test LazyChoicesAction with multiple option strings."""
    action = LazyChoicesAction(
        option_strings=["-f", "--format"],
        dest="format",
        choices_func=lambda: ["short", "long"],
    )

    parser, namespace = mock_parser_namespace

    # Test with long option
    action(parser, namespace, "short", "--format")
    assert namespace.format == "short"

    # Reset namespace
    namespace.format = None
    parser.error_called = False

    # Test with short option
    action(parser, namespace, "long", "-f")
    assert namespace.format == "long"


def test_conda_export_format_integration(export_format_choices):
    """Test LazyChoicesAction with realistic conda export format choices."""
    parser = ArgumentParser(prog="conda export")
    parser.add_argument(
        "--format",
        action=LazyChoicesAction,
        choices_func=lambda: export_format_choices,
        help="Export format",
    )

    # Test valid parsing
    args = parser.parse_args(["--format", "yaml"])
    assert args.format == "yaml"

    # Test help includes choices
    help_text = parser.format_help()
    assert "environment-json" in help_text
    assert "environment-yaml" in help_text
    assert "explicit" in help_text


def test_conda_solver_integration(solver_choices):
    """Test LazyChoicesAction with realistic conda solver choices."""
    parser = ArgumentParser(prog="conda install")
    parser.add_argument(
        "--solver",
        action=LazyChoicesAction,
        choices_func=lambda: solver_choices,
        help="Solver backend",
    )

    # Test valid parsing
    args = parser.parse_args(["--solver", "libmamba"])
    assert args.solver == "libmamba"

    # Test help includes choices
    help_text = parser.format_help()
    assert "{classic,libmamba}" in help_text


def test_real_conda_plugin_manager_integration(conda_cli):
    """Test LazyChoicesAction with real conda plugin manager."""
    from conda.base.context import context

    # Test that the actual plugin manager works with LazyChoicesAction
    formats = context.plugin_manager.get_exporter_format_mapping()
    assert len(formats) > 0
    assert "yaml" in formats
    assert "json" in formats

    # Test that choices are properly sorted
    sorted_formats = sorted(formats)
    assert sorted_formats == sorted(
        context.plugin_manager.get_exporter_format_mapping()
    )
