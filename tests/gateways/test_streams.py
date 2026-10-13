# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
from __future__ import annotations

from typing import TYPE_CHECKING

from conda.gateways.logging import TokenURLFilter
from conda.gateways.streams import redact_token_urls, stderr, stdout

if TYPE_CHECKING:
    from pytest import CaptureFixture


def test_redact_token_urls_matches_token_url_filter():
    """``gateways.streams.redact_token_urls`` must match :class:`TokenURLFilter` (logging handlers)."""
    url = "https://example.com/t/secret-token-abc/channel"
    sanitized = "https://example.com/t/<TOKEN>/channel"
    assert redact_token_urls(url) == TokenURLFilter.TOKEN_REPLACE(url) == sanitized


def test_stderr_writes_redacted_text(capsys: CaptureFixture):
    """``stderr`` prints to stderr and applies token redaction."""
    stdout("test-stdout")
    stderr("test-stderr")
    out, err = capsys.readouterr()
    assert "test-stdout" in out
    assert "test-stderr" in err
