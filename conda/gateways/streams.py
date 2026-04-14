# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""Helper functions for streaming output to stdout and stderr."""

import re
import sys

_TOKEN_URL_PATTERN = re.compile(
    r"(|https?://)"  # \1  scheme
    r"(|\s"  # \2  space, or
    r"|(?:(?:\d{1,3}\.){3}\d{1,3})"  # ipv4, or
    r"|(?:"  # domain name
    r"(?:[a-zA-Z0-9-]{1,20}\.){0,10}"  # non-tld
    r"(?:[a-zA-Z]{2}[a-zA-Z0-9-]{0,18})"  # tld
    r"))"  # end domain name
    r"(|:\d{1,5})?"  # \3  port
    r"/t/[a-z0-9A-Z-]+/"  # token
)


def _redact_token_urls(message: str) -> str:
    """Redact channel tokens in URLs."""
    return _TOKEN_URL_PATTERN.sub(r"\1\2\3/t/<TOKEN>/", message)


def stdout(text: str, **kwargs) -> None:
    # helper replacing conda.stdout logger
    print(_redact_token_urls(text), **kwargs, file=sys.stdout)


def stderr(text: str, **kwargs) -> None:
    # helper replacing conda.stderr logger
    print(_redact_token_urls(text), **kwargs, file=sys.stderr)


def stdoutlog(text: str, **kwargs) -> None:
    # helper replacing conda.stdoutlog and conda.stdout.verbose loggers
    from ..base.context import context

    if not context.json:
        stdout(text, **kwargs)


def stderrlog(text: str, **kwargs) -> None:
    # helper replacing conda.stderrlog logger
    from ..base.context import context

    if not context.json:
        stderr(text, **kwargs)
