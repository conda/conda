# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
# Copyright (C) 2026 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
from __future__ import annotations

from conda.common.user_error import (
    UserErrorHint,
    UserFacingErrorDetails,
    format_user_facing_error,
    user_facing_details_to_json,
)


def test_format_user_facing_error_summary_only() -> None:
    d = UserFacingErrorDetails(summary="Something failed.")
    assert format_user_facing_error(d) == "Something failed.\n"


def test_format_user_facing_error_full() -> None:
    d = UserFacingErrorDetails(
        summary="Summary line.",
        cause="Because of reasons.",
        hints=(
            UserErrorHint("Do A", "do_a"),
            UserErrorHint("Do B", None),
        ),
    )
    out = format_user_facing_error(d)
    assert "Summary line." in out
    assert "Because of reasons." in out
    assert "Next steps:" in out
    assert "1. Do A" in out
    assert "2. Do B" in out


def test_user_facing_details_to_json() -> None:
    d = UserFacingErrorDetails(
        summary="S",
        cause="C",
        hints=(UserErrorHint("h1", "code1"), UserErrorHint("h2", None)),
    )
    j = user_facing_details_to_json(d)
    assert j["summary"] == "S"
    assert j["cause"] == "C"
    assert j["hints"] == [
        {"text": "h1", "hint_code": "code1"},
        {"text": "h2", "hint_code": None},
    ]
    assert j["hint_codes"] == ["code1"]
