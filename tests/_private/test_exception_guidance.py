# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
from __future__ import annotations

import pytest

from conda import CondaError
from conda._private.exception_guidance import ErrorGuidance, GuidanceHint


def test_GuidanceHint() -> None:
    hint = GuidanceHint("Do the thing.", "do_the_thing")
    assert hint.text == "Do the thing."
    assert hint.hint_code == "do_the_thing"


def test_ErrorGuidance_defaults() -> None:
    g = ErrorGuidance(summary="S")
    assert g.summary == "S"
    assert g.cause is None
    assert g.hints == ()


def test_ErrorGuidance_requires_at_least_one_field() -> None:
    with pytest.raises(ValueError, match="at least one of summary, cause, or hints"):
        ErrorGuidance()


def test_ErrorGuidance_full() -> None:
    g = ErrorGuidance(
        summary="Something went wrong.",
        cause="Because of reasons.",
        hints=(
            GuidanceHint("Do A", "do_a"),
            GuidanceHint("Do B", "do_b"),
        ),
    )
    assert g.summary == "Something went wrong."
    assert g.cause == "Because of reasons."
    assert len(g.hints) == 2


def test_ErrorGuidance_frozen() -> None:
    g = ErrorGuidance(summary="Test.")

    with pytest.raises(AttributeError):
        g.summary = "Changed."


def test_format_guidance_summary_only() -> None:
    g = ErrorGuidance(summary="Failed.")
    result = g.format(CondaError("fallback"))
    assert result == "CondaError: Failed."


def test_format_guidance_no_summary_uses_message() -> None:
    g = ErrorGuidance(cause="Root cause.")
    result = g.format(CondaError("default message"))
    assert "CondaError: default message" in result
    assert "Root cause." in result


def test_format_guidance_with_cause() -> None:
    g = ErrorGuidance(summary="Failed.", cause="Root cause.")
    result = g.format(CondaError("fallback"))
    assert "CondaError: Failed." in result
    assert "Cause: Root cause." in result


def test_format_guidance_with_hints() -> None:
    g = ErrorGuidance(
        summary="Failed.",
        hints=(
            GuidanceHint("Do A", "do_a"),
            GuidanceHint("Do B", "do_b"),
        ),
    )
    result = g.format(CondaError("fallback")).splitlines()
    assert result == [
        "CondaError: Failed.",
        "",
        "Next steps:",
        "  - (do_a) Do A",
        "  - (do_b) Do B",
    ]


def test_format_guidance_multiline_command_hint() -> None:
    g = ErrorGuidance(
        summary="Failed.",
        hints=(
            GuidanceHint(
                "Install a specific conda version first, for example:\n"
                "      conda install conda=<version>",
                "install_conda_version",
            ),
        ),
    )
    result = g.format(CondaError("fallback")).splitlines()
    assert result == [
        "CondaError: Failed.",
        "",
        "Next steps:",
        "  - (install_conda_version) Install a specific conda version first, for example:",
        "      conda install conda=<version>",
    ]


def test_format_guidance_full() -> None:
    g = ErrorGuidance(
        summary="Failed.",
        cause="Because of X.",
        hints=(
            GuidanceHint("Try Y.", "try_y"),
            GuidanceHint("Try Z.", "try_z"),
        ),
    )
    result = g.format(CondaError("fallback")).splitlines()
    assert result == [
        "CondaError: Failed.",
        "",
        "Cause: Because of X.",
        "Next steps:",
        "  - (try_y) Try Y.",
        "  - (try_z) Try Z.",
    ]


def test_ErrorGuidance_hint_codes_property() -> None:
    g = ErrorGuidance(
        hints=(
            GuidanceHint("h1", "code1"),
            GuidanceHint("h2", "code2"),
        ),
    )
    assert g.hint_codes == ("code1", "code2")


def test_ErrorGuidance_hint_codes_empty() -> None:
    g = ErrorGuidance(summary="S")
    assert g.hint_codes == ()


def test_ErrorGuidance_json() -> None:
    g = ErrorGuidance(
        summary="S",
        cause="C",
        hints=(
            GuidanceHint("h1", "code1"),
            GuidanceHint("h2", "code2"),
        ),
    )
    j = g.__json__()
    assert j == {
        "summary": "S",
        "cause": "C",
        "hints": (
            {"text": "h1", "hint_code": "code1"},
            {"text": "h2", "hint_code": "code2"},
        ),
        "hint_codes": ("code1", "code2"),
    }


def test_ErrorGuidance_json_no_hints() -> None:
    g = ErrorGuidance(summary="S")
    assert g.__json__() == {"summary": "S"}


def test_coerce_guidance_none() -> None:
    assert ErrorGuidance.coerce(None) is None


def test_coerce_guidance_passthrough() -> None:
    g = ErrorGuidance(summary="Hello.")
    assert ErrorGuidance.coerce(g) is g


def test_coerce_guidance_dict_minimal() -> None:
    g = ErrorGuidance.coerce({"summary": "Hello."})
    assert isinstance(g, ErrorGuidance)
    assert g.summary == "Hello."
    assert g.cause is None
    assert g.hints == ()


def test_coerce_guidance_dict_full() -> None:
    g = ErrorGuidance.coerce(
        {
            "summary": "S",
            "cause": "C",
            "hints": [
                {"text": "h1", "hint_code": "code1"},
                {"text": "h2", "hint_code": "code2"},
            ],
        }
    )
    assert isinstance(g, ErrorGuidance)
    assert g.summary == "S"
    assert g.cause == "C"
    assert len(g.hints) == 2
    assert g.hints[0].text == "h1"
    assert g.hints[0].hint_code == "code1"


def test_coerce_guidance_dict_unknown_keys_ignored() -> None:
    g = ErrorGuidance.coerce(
        {
            "summary": "S",
            "unknown_key": "should be ignored",
        }
    )
    assert g.summary == "S"


def test_coerce_guidance_invalid_type() -> None:
    with pytest.raises(TypeError, match="guidance must be dict or ErrorGuidance"):
        ErrorGuidance.coerce("not a dict or ErrorGuidance")  # type: ignore[arg-type]
