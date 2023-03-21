# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""Placeholder for the actual version code injected by hatch-vcs.

The logic here is used during development installs only so keep it simple. Since conda
abides by CEP-8, which outlines using CalVer, our development version is simply:
    YY.MM.0.devN+HASH[.dirty]
"""
from contextlib import suppress
from datetime import date
from pathlib import Path
from subprocess import run, CalledProcessError

from .common.compat import on_win

dev = "0"
commit = "nogit"
dirty = ""
with suppress(CalledProcessError, ValueError):
    # CalledProcessError: git isn't installed, or an older git is installed
    # ValueError: unable to split describe string
    path = Path(__file__).parent

    response = run(
        ["git", "-C", path, "rev-parse", "--short", "HEAD"],
        check=True,
        capture_output=True,
        text=True,
    )
    if response.stdout and not response.stderr:
        commit = response.stdout.strip()

    response = run(
        [
            "git",
            "-C",
            path,
            "describe",
            "--tags",
            "--always",
            "--long",
            "--first-parent",
            "--dirty",
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    if response.stdout and not response.stderr:
        _, dev, _ = response.stdout.strip().split("-", 2)

        if response.stdout.strip().endswith("-dirty"):
            dirty = ".dirty"


if on_win:
    __version__ = f"{date.today():%y.%#m}.0.dev{dev}+{commit}{dirty}"
else:
    __version__ = f"{date.today():%y.%-m}.0.dev{dev}+{commit}{dirty}"
