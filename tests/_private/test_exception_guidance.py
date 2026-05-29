# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
from __future__ import annotations

from dataclasses import asdict

from conda._private.exception_guidance import (
    ErrorGuidance,
    GuidanceHint,
    _coerce_guidance,
    format_guidance,
)


def test_GuidanceHint() -> None:
    hint = GuidanceHint("Do the thing.", "do_the_thing")
    assert hint.text == "Do the thing."
    assert hint.hint_code == "do_the_thing"


def test_ErrorGuidance_defaults() -> None:
    g = ErrorGuidance()
    assert g.summary is None
    assert g.cause is None
    assert g.hints == ()


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
    import pytest

    with pytest.raises(AttributeError):
        g.summary = "Changed."


def test_format_guidance_summary_only() -> None:
    g = ErrorGuidance(summary="Failed.")
    result = format_guidance(g, "fallback message")
    assert result == "Failed."


def test_format_guidance_no_summary_uses_message() -> None:
    g = ErrorGuidance()
    result = format_guidance(g, "default message")
    assert result == "default message"


def test_format_guidance_with_cause() -> None:
    g = ErrorGuidance(summary="Failed.", cause="Root cause.")
    result = format_guidance(g, "fallback")
    assert "Failed." in result
    assert "Cause: Root cause." in result


def test_format_guidance_with_hints() -> None:
    g = ErrorGuidance(
        summary="Failed.",
        hints=(
            GuidanceHint("Do A", "do_a"),
            GuidanceHint("Do B", "do_b"),
        ),
    )
    result = format_guidance(g, "fallback")
    assert "Next steps:" in result
    assert "1. Do A (do_a)" in result
    assert "2. Do B (do_b)" in result


def test_format_guidance_full() -> None:
    g = ErrorGuidance(
        summary="Failed.",
        cause="Because of X.",
        hints=(
            GuidanceHint("Try Y.", "try_y"),
            GuidanceHint("Try Z.", "try_z"),
        ),
    )
    result = format_guidance(g, "fallback")
    assert "Failed." in result
    assert "Cause: Because of X." in result
    assert "Next steps:" in result
    assert "1. Try Y. (try_y)" in result
    assert "2. Try Z. (try_z)" in result


def test_ErrorGuidance_hint_codes_computed() -> None:
    g = ErrorGuidance(
        summary="S",
        hints=(
            GuidanceHint("h1", "code1"),
            GuidanceHint("h2", "code2"),
        ),
    )
    assert g.hint_codes == ("code1", "code2")


def test_ErrorGuidance_hint_codes_empty() -> None:
    g = ErrorGuidance()
    assert g.hint_codes == ()


def test_ErrorGuidance_asdict_includes_hint_codes() -> None:
    g = ErrorGuidance(
        summary="S",
        hints=(
            GuidanceHint("h1", "code1"),
            GuidanceHint("h2", "code2"),
        ),
    )
    d = asdict(g)
    assert d["hint_codes"] == ("code1", "code2")
    assert d["hints"] == (
        {"text": "h1", "hint_code": "code1"},
        {"text": "h2", "hint_code": "code2"},
    )
    assert d["summary"] == "S"
    assert d["cause"] is None


def test_coerce_guidance_none() -> None:
    assert _coerce_guidance(None) is None


def test_coerce_guidance_passthrough() -> None:
    g = ErrorGuidance(summary="Hello.")
    assert _coerce_guidance(g) is g


def test_coerce_guidance_dict_minimal() -> None:
    g = _coerce_guidance({"summary": "Hello."})
    assert isinstance(g, ErrorGuidance)
    assert g.summary == "Hello."
    assert g.cause is None
    assert g.hints == ()


def test_coerce_guidance_dict_full() -> None:
    g = _coerce_guidance(
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
    g = _coerce_guidance(
        {
            "summary": "S",
            "unknown_key": "should be ignored",
        }
    )
    assert g.summary == "S"
    # unknown_key is simply ignored by the dict parsing


def test_coerce_guidance_invalid_type() -> None:
    import pytest

    with pytest.raises(TypeError, match="guidance must be dict or ErrorGuidance"):
        _coerce_guidance("not a dict or ErrorGuidance")  # type: ignore[arg-type]
