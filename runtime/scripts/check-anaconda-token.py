#!/usr/bin/env python3
# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""Check Anaconda.org release credentials without changing repository state."""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request

API_URL = "https://api.anaconda.org"


def authentication(token: str) -> dict[str, object]:
    request = urllib.request.Request(
        f"{API_URL}/authentication",
        headers={
            "Accept": "application/json",
            "Authorization": f"token {token}",
            "User-Agent": "conda-runtime-release",
            "x-binstar-api-version": "1.12.2",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            value = json.load(response)
    except urllib.error.HTTPError as error:
        raise SystemExit(
            f"Anaconda.org rejected ANACONDA_API_TOKEN with HTTP {error.code}."
        ) from None
    if not isinstance(value, dict):
        raise SystemExit("Anaconda.org returned invalid authentication metadata.")
    return value


def main() -> None:
    token = os.environ.get("ANACONDA_API_TOKEN")
    owner = "conda"
    if not token:
        raise SystemExit("ANACONDA_API_TOKEN is not set.")

    value = authentication(token)
    raw_scopes = value.get("scopes")
    if not isinstance(raw_scopes, list) or not all(
        isinstance(scope, str) for scope in raw_scopes
    ):
        raise SystemExit("Anaconda.org returned invalid token scopes.")
    scopes = set(raw_scopes)
    if not scopes.intersection({"all", "api", "api:write"}):
        raise SystemExit(
            "ANACONDA_API_TOKEN cannot write through the Anaconda.org API."
        )
    if not scopes.intersection({"all", "repos", "conda"}):
        raise SystemExit("ANACONDA_API_TOKEN cannot manage conda repositories.")

    print(
        f"Anaconda.org token has upload scopes. Release channel: {owner}/label/runtime."
    )


if __name__ == "__main__":
    main()
