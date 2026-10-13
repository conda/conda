# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

import pytest

from conda.notices import cache as notices_cache
from conda.notices import core as notices_core

if TYPE_CHECKING:
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
    """``clear_cache()`` must leave ``notices.cache`` empty and looking expired."""
    notices_cache_file.write_text("\n".join(viewed_ids))
    notices_cache_file.touch()
    assert not notices_core.is_channel_notices_cache_expired()

    notices_cache.clear_cache()

    assert notices_cache_file.is_file()
    assert notices_cache_file.read_text() == ""
    assert notices_core.is_channel_notices_cache_expired()


def test_clear_cache_removes_channel_response_caches(
    notices_cache_file: Path,
    channel_response_cache: Path,
) -> None:
    """Per-channel response cache files are removed by ``clear_cache()``."""
    assert channel_response_cache.is_file()
    notices_cache.clear_cache()
    assert not channel_response_cache.exists()


@pytest.mark.parametrize(
    "failing_target",
    ["channel_response_cache", "notices_cache"],
)
def test_clear_cache_survives_os_error(
    notices_cache_file: Path,
    channel_response_cache: Path,
    monkeypatch: MonkeyPatch,
    failing_target: str,
) -> None:
    """
    ``clear_cache()`` must tolerate ``OSError`` from either the per-channel
    unlink or the ``notices.cache`` rewrite (e.g. Windows file locks from
    antivirus scanners or lingering handles).
    """
    if failing_target == "channel_response_cache":
        original_unlink = Path.unlink

        def fake_unlink(self: Path, *args, **kwargs):
            if self == channel_response_cache:
                raise PermissionError("simulated Windows lock")
            return original_unlink(self, *args, **kwargs)

        monkeypatch.setattr(Path, "unlink", fake_unlink)
    else:

        def fake_open(*args, **kwargs):
            raise PermissionError("simulated Windows lock")

        monkeypatch.setattr("conda.notices.cache.open", fake_open, raising=False)

    notices_cache.clear_cache()

    if failing_target == "channel_response_cache":
        assert notices_core.is_channel_notices_cache_expired()
