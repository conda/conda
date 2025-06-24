# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""Installer for pip packages from a direct reference (e.g. by a URL)."""

from __future__ import annotations

from typing import TYPE_CHECKING

from ...reporters import get_spinner
from .pip import _pip_install_via_requirements

if TYPE_CHECKING:
    from argparse import Namespace

    from ...direct import DirectPackageMetadata, DirectPackages, DirectPackageURL


def _pip_spec(url: DirectPackageURL, metadata: DirectPackageMetadata) -> str:
    # Add a hash to the URL fragment when available
    # Avoid --hash is this enabled hash-checking for all requirements
    # https://pip.pypa.io/en/stable/topics/secure-installs/#hash-checking-mode
    if "sha256" in metadata:
        return f"{url}#sha256={metadata['sha256']}"
    return url


def install(prefix: str, specs: DirectPackages, args: Namespace, *_, **kwargs):
    pip_specs = tuple(_pip_spec(url, metadata) for url, metadata in specs.items())
    with get_spinner("Installing pip dependencies"):
        return _pip_install_via_requirements(prefix, pip_specs, args)
