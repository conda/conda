# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""Tests for the env-setup preview register() entry point."""

from __future__ import annotations

from conda._preview.env_setup import PREVIEW_LABEL, register
from conda.base.context import context, reset_context


def test_preview_label():
    """PREVIEW_LABEL must match the kebab-case name used in context.preview."""
    assert PREVIEW_LABEL == "env-setup"


def test_register_is_callable():
    """register must be importable and callable."""
    assert callable(register)


def test_register_noop(monkeypatch):
    """register(context) is a no-op stub: returns None with no side effects."""
    monkeypatch.setenv("CONDA_PREVIEW", "env-setup")
    reset_context()

    result = register(context)

    assert result is None
