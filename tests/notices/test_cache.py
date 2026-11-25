# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from conda.notices import cache as notices_cache

if TYPE_CHECKING:
    from pathlib import Path

    from pytest import MonkeyPatch


@pytest.fixture
def channel_response_cache(notices_cache_dir: Path) -> Path:
    """Create a dummy per-channel response cache file inside ``notices_cache_dir``."""
    path = notices_cache_dir / "chan.json"
    path.write_text("{}")
    return path


@pytest.fixture
def notices_cache_file(notices_cache_dir: Path) -> Path:
    """Ensure the ``notices.cache`` file exists and return its path."""
    return notices_cache.get_notices_cache_file()


@pytest.mark.parametrize(
    "viewed_ids",
    [(), ("some-id-1", "some-id-2")],
    ids=["empty", "with-viewed-ids"],
)
def test_clear_cache_invalidates_notices_cache(
    notices_cache_file: Path, viewed_ids: tuple[str, ...]
) -> None:
    """``clear_cache()`` must leave ``notices.cache`` empty."""
    notices_cache_file.write_text("\n".join(viewed_ids))

    notices_cache.clear_cache()

    assert notices_cache_file.is_file()
    assert notices_cache_file.read_text() == ""


def test_clear_cache_removes_channel_response_caches(
    notices_cache_file: Path,
    channel_response_cache: Path,
) -> None:
    """Per-channel response cache files are removed by ``clear_cache()``."""
    assert channel_response_cache.is_file()
    notices_cache.clear_cache()
    assert not channel_response_cache.exists()


def test_clear_cache_survives_os_error(
    notices_cache_file: Path,
    channel_response_cache: Path,
    monkeypatch: MonkeyPatch,
) -> None:
    """
    ``clear_cache()`` must tolerate ``OSError`` from either the per-channel
    unlink or the ``notices.cache`` rewrite (e.g. Windows file locks from
    antivirus scanners or lingering handles).
    """

    def fake_open(*args, **kwargs):
        raise PermissionError("simulated Windows lock")

    monkeypatch.setattr("conda.notices.cache.open", fake_open, raising=False)

    notices_cache.clear_cache()
