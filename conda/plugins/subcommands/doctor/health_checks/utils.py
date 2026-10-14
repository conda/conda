# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""Health check: Helpful shared functions for performing health checks."""

from __future__ import annotations

from logging import getLogger
from pathlib import Path

from .....common.serialize import json

logger = getLogger(__name__)


def get_spec_str_from_conda_meta(
    prefix: str, packages: list[str]
) -> tuple[list[str], list[str]]:
    """
    Get a list of specs (specified with name, version, and build) from the prefix
    matching the name of the requested packages. The conda-meta is generally assumed
    to be intact. However, uf the name, version or build metadata is incomplete, the
    package will be skipped.
    """
    specs = []
    skipped = []
    for stem in packages:
        try:
            metadata = json.loads(
                (Path(prefix) / "conda-meta" / f"{stem}.json").read_text()
            )
            specs.append(
                f"{metadata['name']}={metadata['version']}={metadata['build']}"
            )
        except KeyError:
            skipped.append(stem)
    return specs, skipped


def get_name_from_conda_meta_file_name(conda_meta_filename: str):
    """Given the name of a package conda_meta file, extract the name of the package"""
    name_version_build_string = Path(conda_meta_filename).name.removesuffix(".json")
    return name_version_build_string.rsplit("-", 2)[0]
