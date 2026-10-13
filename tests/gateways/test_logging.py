# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
import logging
import os
import sys
from logging import getLogger
from pathlib import Path
from subprocess import run

import pytest

from conda.auxlib.ish import dals
from conda.gateways.logging import (
    TokenURLFilter,
    initialize_logging,
    set_all_logger_level,
)

log = getLogger(__name__)


TR = TokenURLFilter.TOKEN_REPLACE


def test_token_replace_big_string():
    test_string = dals(
        """
    555.123.4567	+1-(800)-555-2468
    foo@demo.net	bar.ba@test.co.uk
    www.demo.com	http://foo.co.uk/t/tk-abkdehc1n38cCBDHN-cje/more/stuf/like/this.html?q=bar
    http://regexr.com/t/tk-abkdehc1n38cCBDHN-cje/more/stuf/like/this.html?q=bar
    https://mediatemple.net/t/tk-abkdehc1n38cCBDHN-cje/more/stuf/like/this.html?q=bar

      http://132.154.8.8:1010/t/tk-abkdehc1n38cCBDHN-cje/more/stuf/like/this.html?q=bar

     /t/tk-abkdehc1n38cCBDHN-cje/more/stuf/like/this.html?q=bar
    /t/tk-abkdehc1n38cCBDHN-cje/more/stuf/like/this.html?q=bar


      https://mediatemple.net/t/tk-abkdehc1n38cCBDHN-cje/more/stuf/like/this.html?q=bar

    http://foo.co.uk:8080/t/tk-abkdehc1n38cCBDHN-cje/more/stuf/like/this.html?q=bar

    """
    )
    result_string = dals(
        """
    555.123.4567	+1-(800)-555-2468
    foo@demo.net	bar.ba@test.co.uk
    www.demo.com	http://foo.co.uk/t/<TOKEN>/more/stuf/like/this.html?q=bar
    http://regexr.com/t/<TOKEN>/more/stuf/like/this.html?q=bar
    https://mediatemple.net/t/<TOKEN>/more/stuf/like/this.html?q=bar

      http://132.154.8.8:1010/t/<TOKEN>/more/stuf/like/this.html?q=bar

     /t/<TOKEN>/more/stuf/like/this.html?q=bar
    /t/<TOKEN>/more/stuf/like/this.html?q=bar


      https://mediatemple.net/t/<TOKEN>/more/stuf/like/this.html?q=bar

    http://foo.co.uk:8080/t/<TOKEN>/more/stuf/like/this.html?q=bar

    """
    )
    print(TR(test_string))
    assert TR(test_string) == result_string


def test_token_replace_individual_strings():
    assert (
        TR(
            "http://foo.co.uk:8080/t/tk-abkdehc1n38cCBDHN-cje/more/stuf/like/this.html?q=bar"
        )
        == "http://foo.co.uk:8080/t/<TOKEN>/more/stuf/like/this.html?q=bar"
    )
    assert (
        TR("     /t/tk-abkdehc1n38cCBDHN-cje/more/stuf/like/this.html?q=bar")
        == "     /t/<TOKEN>/more/stuf/like/this.html?q=bar"
    )
    assert (
        TR("/t/tk-abkdehc1n38cCBDHN-cje/more/stuf/like/this.html?q=bar")
        == "/t/<TOKEN>/more/stuf/like/this.html?q=bar"
    )


@pytest.mark.integration
def test_token_not_present_in_conda_create(tmp_path: Path):
    """
    Test that tokens in channel URLs are never leaked in verbose output.

    The test verifies that when a channel URL containing a token is used,
    the raw token value does not appear anywhere in the command output.

    Note: We previously also checked for '/t/<TOKEN>/' in the output to verify
    the TokenURLFilter was being applied, but this was unreliable because:
    1. Channel URLs are parsed early and tokens are extracted/stored separately
    2. Most logging uses the clean URL (without /t/token/) for display
    3. Token URLs only appear in HTTP request logging, which may not trigger
       with cached repodata or --dry-run mode

    Other tests verify the filter works correctly (test_token_replace_*,
    test_token_url_filter_formats). This integration test focuses on the
    security guarantee: tokens don't leak.
    """
    initialize_logging()
    env = os.environ.copy()
    env["CONDA_CHANNELS"] = (
        "https://conda.anaconda.org/t/xx-00000000-0000-0000-0000-000000000000/conda-test"
    )
    p = run(
        [
            sys.executable,
            "-mconda",
            "-vvvv",
            "create",
            "--dry-run",
            "--prefix",
            tmp_path / "env",
            "ca-certificates",
        ],
        env=env,
        capture_output=True,
        text=True,
    )
    print(p.stdout)
    print(p.stderr, file=sys.stderr)
    all_output = p.stdout + "\n" + p.stderr

    # The critical security guarantee: raw tokens must never appear in output
    assert "/t/xx-00000000-0000-0000-0000-000000000000" not in all_output


def test_token_url_filter_attached_to_loggers():
    """
    Test that TokenURLFilter is properly attached to conda loggers after initialization.

    This verifies the logging integration is set up correctly. The actual filtering
    behavior is tested by the parametrized test_token_url_filter_formats test.
    """
    initialize_logging()
    set_all_logger_level(logging.DEBUG)

    conda_logger = getLogger("conda")

    # Verify TokenURLFilter is attached to at least one handler
    filter_found = any(
        isinstance(f, TokenURLFilter)
        for handler in conda_logger.handlers
        for f in handler.filters
    )

    assert filter_found, "TokenURLFilter should be attached to conda logger handlers"


@pytest.mark.parametrize(
    "input_url,expected_present,expected_absent",
    [
        pytest.param(
            "https://conda.anaconda.org/t/tk-12345/conda-forge/linux-64/repodata.json",
            "/t/<TOKEN>/conda-forge",
            "tk-12345",
            id="https-url-with-token",
        ),
        pytest.param(
            "http://10.0.0.1:8080/t/secret-token-abc/channel/path",
            "/t/<TOKEN>/channel",
            "secret-token-abc",
            id="http-ip-port-with-token",
        ),
        pytest.param(
            "/t/my-token-123/some/path",
            "/t/<TOKEN>/some",
            "my-token-123",
            id="path-only-with-token",
        ),
        pytest.param(
            "URL1: /t/token1/path1 and URL2: /t/token2/path2",
            "/t/<TOKEN>/",
            "token1",
            id="multiple-tokens-in-message",
        ),
    ],
)
def test_token_url_filter_formats(input_url, expected_present, expected_absent):
    """
    Test that TokenURLFilter handles various token URL formats correctly.
    """
    result = TR(input_url)
    assert expected_present in result
    assert expected_absent not in result
