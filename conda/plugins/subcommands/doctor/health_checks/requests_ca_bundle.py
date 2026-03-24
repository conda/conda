# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""Health check: REQUESTS_CA_BUNDLE environment variable."""

from __future__ import annotations

import os
from pathlib import Path
from typing import TYPE_CHECKING

from requests.exceptions import RequestException

from .....base.constants import OK_MARK, X_MARK
from .....base.context import context
from .....gateways.connection.session import get_session
from .... import hookimpl
from ....types import CondaHealthCheck

if TYPE_CHECKING:
    from collections.abc import Iterable


def requests_ca_bundle_check(prefix: str, verbose: bool) -> None:
    """Health check action: Verify REQUESTS_CA_BUNDLE environment variable."""
    # Use a channel aliases url since users may be on an intranet and
    # have customized their conda setup to point to an internal mirror.
    ca_bundle_test_url = context.channel_alias.urls()[0]

    requests_ca_bundle = os.getenv("REQUESTS_CA_BUNDLE")
    if not requests_ca_bundle:
        return
    elif not Path(requests_ca_bundle).exists():
        print(
            f"{X_MARK} Env var `REQUESTS_CA_BUNDLE` is pointing to a non existent file.\n"
        )
    else:
        session = get_session(ca_bundle_test_url)
        try:
            response = session.get(ca_bundle_test_url)
            response.raise_for_status()
            print(f"{OK_MARK} `REQUESTS_CA_BUNDLE` was verified.\n")
        except (OSError, RequestException) as e:
            print(
                f"{X_MARK} The following error occured while verifying `REQUESTS_CA_BUNDLE`: {e}\n"
            )


@hookimpl
def conda_health_checks() -> Iterable[CondaHealthCheck]:
    """Register the REQUESTS_CA_BUNDLE health check."""
    yield CondaHealthCheck(
        name="requests-ca-bundle",
        action=requests_ca_bundle_check,
        summary="Check REQUESTS_CA_BUNDLE environment variable",
    )
