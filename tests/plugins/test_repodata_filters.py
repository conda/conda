# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""Tests for the conda_repodata_filters plugin hook."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from conda.common.serialize import json
from conda.core.subdir_data import SubdirData
from conda.models.channel import Channel
from conda.plugins import hookimpl
from conda.plugins.manager import get_plugin_manager
from conda.plugins.types import CondaRepodataFilter

if TYPE_CHECKING:
    from pathlib import Path


PLATFORM = "linux-64"


@pytest.fixture
def filter_channel(tmp_path: Path) -> Channel:
    subdir_path = tmp_path / PLATFORM
    subdir_path.mkdir()

    pkg_base = {
        "build": "0",
        "build_number": 0,
        "depends": [],
        "md5": "d41d8cd98f00b204e9800998ecf8427e",
        "size": 100,
        "subdir": PLATFORM,
        "version": "1.0",
    }

    repodata = {
        "info": {"subdir": PLATFORM},
        "packages": {
            "alpha-1.0-0.tar.bz2": {**pkg_base, "name": "alpha"},
            "beta-1.0-0.tar.bz2": {**pkg_base, "name": "beta"},
            "gamma-1.0-0.tar.bz2": {**pkg_base, "name": "gamma"},
        },
        "packages.conda": {},
    }

    (subdir_path / "repodata.json").write_text(json.dumps(repodata))
    return Channel(str(subdir_path))


def _make_exclude_plugin(pkg_name: str):
    """Return a module-like object that registers a repodata filter excluding *pkg_name*."""

    @hookimpl
    def conda_repodata_filters():
        yield CondaRepodataFilter(
            name=f"exclude-{pkg_name}",
            filter=lambda fn, info, _n=pkg_name: info["name"] != _n,
        )

    return type(
        f"_Exclude{pkg_name.title()}",
        (),
        {"conda_repodata_filters": staticmethod(conda_repodata_filters)},
    )()


@pytest.fixture
def register_filters():
    """Context-manager fixture that registers and unregisters filter plugins."""
    pm = get_plugin_manager()
    registered = []

    def _register(*pkg_names: str):
        for name in pkg_names:
            plugin = _make_exclude_plugin(name)
            pm.register(plugin, name=f"test-exclude-{name}")
            registered.append(f"test-exclude-{name}")
        SubdirData.clear_cached_local_channel_data()

    yield _register

    for name in registered:
        pm.unregister(name=name)


@pytest.mark.parametrize(
    "exclude, expected_in, expected_out",
    [
        pytest.param(
            ["beta"],
            {"alpha", "gamma"},
            {"beta"},
            id="single-filter",
        ),
        pytest.param(
            ["beta", "gamma"],
            {"alpha"},
            {"beta", "gamma"},
            id="multiple-filters-compose",
        ),
    ],
)
def test_repodata_filter_plugin(
    filter_channel: Channel,
    register_filters,
    exclude: list[str],
    expected_in: set[str],
    expected_out: set[str],
):
    register_filters(*exclude)
    sd = SubdirData(channel=filter_channel)
    names = {rec.name for rec in sd.iter_records()}

    for name in expected_in:
        assert name in names, f"{name} should be included"
    for name in expected_out:
        assert name not in names, f"{name} should be excluded"
