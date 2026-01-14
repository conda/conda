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
def food_choices():
    """Fixture providing realistic food choices."""
    return ["spam", "eggs", "bacon", "spam"]


@pytest.fixture
def solver_choices():
    """Fixture providing realistic solver choices."""
    return ["classic", "libmamba"]


@pytest.fixture
def export_format_choices():
    """Fixture providing realistic export format choices."""
    return ["environment-json", "environment-yaml", "explicit", "json", "yaml"]


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

    # Second access - should use cached result (with caching)
    choices2 = action.choices
    assert choices2 == ["option1", "option2", "option3"]
    assert choices_func_counter.call_count() == 1  # Same count due to caching


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


@pytest.mark.parametrize("valid_choice", ["red", "green", "blue"])
def test_valid_choice_handling(valid_choice, simple_choices, mock_parser_namespace):
    """Test action call with valid choices."""
    action = LazyChoicesAction(
        option_strings=["--test"],
        dest="test",
        choices_func=lambda: simple_choices,
    )
    parser, namespace = mock_parser_namespace

    # Valid choice should set attribute without error
    action(parser, namespace, valid_choice, "--test")
    assert getattr(namespace, "test") == valid_choice
    assert not parser.error_called


@pytest.mark.parametrize("invalid_choice", ["purple", "yellow", "orange"])
def test_invalid_choice_handling(invalid_choice, simple_choices, mock_parser_namespace):
    """Test action call with invalid choices."""
    action = LazyChoicesAction(
        option_strings=["--test"],
        dest="test",
        choices_func=lambda: simple_choices,
    )
    parser, namespace = mock_parser_namespace

    # Invalid choice should call parser.error
    action(parser, namespace, invalid_choice, "--test")
    assert parser.error_called
    assert f"invalid choice: '{invalid_choice}'" in parser.error_message
    assert "choose from 'red', 'green', 'blue'" in parser.error_message


@pytest.mark.parametrize(
    "choices,expected_help_text",
    [
        (["red", "green", "blue"], "{red,green,blue}"),
        (["spam", "eggs", "bacon", "spam"], "{spam,eggs,bacon,spam}"),
        (["classic", "libmamba"], "{classic,libmamba}"),
    ],
)
def test_argumentparser_help_integration(choices, expected_help_text):
    """Test that LazyChoicesAction works with ArgumentParser help generation."""
    parser = ArgumentParser(prog="test")
    parser.add_argument(
        "--option",
        action=LazyChoicesAction,
        choices_func=lambda: choices,
        help="Choose an option",
    )

    # Get help text
    help_output = parser.format_help()

    # Should show choices in help
    assert expected_help_text in help_output
    assert "Choose an option" in help_output


@pytest.mark.parametrize(
    "choices,invalid_choice",
    [
        (["alpha", "beta", "gamma"], "invalid"),
        (["one", "two", "three"], "four"),
        (["yes", "no"], "maybe"),
    ],
)
def test_argumentparser_error_handling(choices, invalid_choice):
    """Test that LazyChoicesAction error handling works with ArgumentParser."""
    parser = ArgumentParser(prog="test")
    parser.add_argument(
        "--choice",
        action=LazyChoicesAction,
        choices_func=lambda: choices,
    )

    # Should raise SystemExit for invalid choice
    with pytest.raises((SystemExit, argparse.ArgumentError)):
        parser.parse_args(["--choice", invalid_choice])


@pytest.mark.parametrize(
    "choices,valid_choice",
    [
        (["one", "two", "three"], "two"),
        (["alpha", "beta", "gamma"], "gamma"),
        (["yes", "no"], "yes"),
    ],
)
def test_argumentparser_valid_parsing(choices, valid_choice):
    """Test that LazyChoicesAction works correctly with valid parsing."""
    parser = ArgumentParser(prog="test")
    parser.add_argument(
        "--number",
        action=LazyChoicesAction,
        choices_func=lambda: choices,
    )

    # Valid choice should parse correctly
    args = parser.parse_args(["--number", valid_choice])
    assert args.number == valid_choice


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


@pytest.mark.parametrize(
    "iterable_choices,valid_choice",
    [
        ({"set", "of", "choices"}, "set"),  # set
        (("tuple", "of", "choices"), "tuple"),  # tuple
        (iter(["iter", "of", "choices"]), "iter"),  # iterator
    ],
)
def test_non_list_iterable_choices(
    iterable_choices, valid_choice, mock_parser_namespace
):
    """Test that choices_func can return any iterable."""
    action = LazyChoicesAction(
        option_strings=["--test"],
        dest="test",
        choices_func=lambda: iterable_choices,
    )

    parser, namespace = mock_parser_namespace

    # Valid choice from iterable should work
    action(parser, namespace, valid_choice, "--test")
    assert namespace.test == valid_choice
    assert not parser.error_called


@pytest.mark.parametrize(
    "option_strings,dest,test_option",
    [
        (["-f", "--food"], "food", "--food"),
        (["-f", "--food"], "food", "-f"),
        (["-s", "--solver"], "solver", "--solver"),
        (["-s", "--solver"], "solver", "-s"),
    ],
)
def test_multiple_option_strings(
    option_strings, dest, test_option, mock_parser_namespace
):
    """Test LazyChoicesAction with multiple option strings."""
    action = LazyChoicesAction(
        option_strings=option_strings,
        dest=dest,
        choices_func=lambda: ["option1", "option2"],
    )

    parser, namespace = mock_parser_namespace

    # Test with specified option
    action(parser, namespace, "option1", test_option)
    assert getattr(namespace, dest) == "option1"
    assert not parser.error_called


# Realistic integration tests - these test actual conda use cases
@pytest.mark.parametrize(
    "prog,option,choices_fixture,valid_choice,help_pattern",
    [
        ("conda food", "--food", "food_choices", "bacon", "{spam,eggs,bacon,spam}"),
        (
            "conda install",
            "--solver",
            "solver_choices",
            "libmamba",
            "{classic,libmamba}",
        ),
    ],
)
def test_conda_integration(
    prog, option, choices_fixture, valid_choice, help_pattern, request
):
    """Test LazyChoicesAction with realistic conda scenarios."""
    choices = request.getfixturevalue(choices_fixture)

    parser = ArgumentParser(prog=prog)
    parser.add_argument(
        option,
        action=LazyChoicesAction,
        choices_func=lambda: choices,
        help=f"{option.lstrip('--').title()} option",
    )

    # Test valid parsing
    args = parser.parse_args([option, valid_choice])
    assert getattr(args, option.lstrip("--")) == valid_choice

    # Test help includes choices
    help_text = parser.format_help()
    assert help_pattern in help_text


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
