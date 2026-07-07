# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
from __future__ import annotations

import json
from typing import TYPE_CHECKING

from conda.notices.cache import get_notices_cache_file
from conda.plugins.clean_paths.notices import find_notices_cache_paths

if TYPE_CHECKING:
    from pathlib import Path

    from conda.testing.fixtures import CondaCLIFixture


def test_find_notices_cache_paths(notices_cache_dir: Path):
    channel_cache = notices_cache_dir / "chan.json"
    channel_cache.write_text("{}")
    notices_cache_file = get_notices_cache_file()
    notices_cache_file.write_text("viewed-id\n")

    paths = set(find_notices_cache_paths("/unused/prefix"))

    assert paths == {str(channel_cache), str(notices_cache_file)}


def test_clean_notices_cache(
    clear_plugin_manager_cache,
    notices_cache_dir: Path,
    conda_cli: CondaCLIFixture,
):
    channel_cache = notices_cache_dir / "chan.json"
    channel_cache.write_text("{}")
    notices_cache_file = get_notices_cache_file()
    notices_cache_file.write_text("viewed-id\n")

    stdout, _, _ = conda_cli("clean", "--notices-cache", "--yes", "--json")
    result = json.loads(stdout)

    assert set(result["clean_paths"]["notices-cache"]["files"]) == {
        str(channel_cache),
        str(notices_cache_file),
    }
    assert not channel_cache.exists()
    assert not notices_cache_file.exists()
