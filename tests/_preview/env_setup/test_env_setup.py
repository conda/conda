# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""Tests for the env-setup preview register() entry point."""

from __future__ import annotations

from conda._preview.env_setup import PREVIEW_LABEL


def test_preview_label():
    """PREVIEW_LABEL must match the kebab-case name used in context.preview."""
    assert PREVIEW_LABEL == "env-setup"
