# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
from __future__ import annotations

from contextlib import nullcontext

import pytest

from conda.exceptions import LinkSourceNotFoundError
from conda.gateways.disk import create
from conda.gateways.disk.create import create_link
from conda.models.enums import LinkType


@pytest.mark.parametrize(
    "function,raises",
    [
        ("extract_tarball", TypeError),
    ],
)
def test_deprecations(function: str, raises: type[Exception] | None) -> None:
    raises_context = pytest.raises(raises) if raises else nullcontext()
    with pytest.deprecated_call(), raises_context:
        getattr(create, function)()


def test_create_link_missing_source_raises_link_source_not_found(tmp_path):
    src = str(tmp_path / "missing-source")
    dst = str(tmp_path / "destination")

    with pytest.raises(LinkSourceNotFoundError) as exc:
        create_link(src, dst, LinkType.softlink)

    assert exc.value.src == src
