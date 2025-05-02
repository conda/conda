# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
from __future__ import annotations

import pytest

with pytest.deprecated_call():
    import conda.plan


@pytest.mark.parametrize(
    "constant",
    [
        "sys",
        "defaultdict",
        "log",
        "IndexedSet",
        "DEFAULTS_CHANNEL_NAME",
        "UNKNOWN_CHANNEL",
        "context",
        "reset_context",
        "TRACE",
        "dashlist",
        "env_vars",
        "time_recorder",
        "groupby",
        "LAST_CHANNEL_URLS",
        "PrefixSetup",
        "UnlinkLinkTransaction",
        "FETCH",
        "LINK",
        "SYMLINK_CONDA",
        "UNLINK",
        "Channel",
        "prioritize_channels",
        "Dist",
        "LinkType",
        "MatchSpec",
        "PackageRecord",
        "normalized_version",
        "human_bytes",
        "log",
    ],
)
def test_deprecations(constant: str) -> None:
    with pytest.deprecated_call():
        getattr(conda.plan, constant)
