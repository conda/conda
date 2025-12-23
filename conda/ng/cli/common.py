"""
Common utilities for the CLI layer.
"""

from __future__ import annotations

from pathlib import Path


def cache_dir() -> Path:
    from conda.base.context import context

    for pkgs_dir in context.pkgs_dirs:
        return Path(pkgs_dir, "cache")
