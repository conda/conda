# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
from __future__ import annotations

import pytest

from conda.common.path import python as python_path
from conda.common.path.python import (
    get_python_site_packages_short_path,
    is_valid_import_path,
)


@pytest.mark.parametrize(
    "path,result",
    [
        ("python", True),
        ("python.path", True),
        ("python._path0123", True),
        # Keywords are forbidden
        ("import", False),
        ("import.path", False),
        # Numbers cannot start the name
        ("0mod.import", False),
        # Empty strings or components are not valid
        ("", False),
        (".", False),
        ("..", False),
        # This also applies to relative imports
        (".base.common", False),
        ("..parent.base.common", False),
        # Some non-ASCII characters are ok!
        ("ñándú", True),
        ("ñ.α", True),
        # Emojis are not
        ("🚨", False),
        ("a🚨", False),
        # Injection prevented
        ('something"); malicious()', False),
    ],
)
def test_is_valid_import_path(path, result):
    assert is_valid_import_path(path) is result


def test_get_python_site_packages_short_path_none():
    assert get_python_site_packages_short_path(None) is None


@pytest.mark.parametrize(
    "python_version,expected",
    [
        ("2.7", "lib/python2.7/site-packages"),
        ("3.14", "lib/python3.14/site-packages"),
        ("3.15", "lib/python3.15/site-packages"),
        ("3.15.0", "lib/python3.15/site-packages"),
        ("3.16.1", "lib/python3.16/site-packages"),
        ("315", "lib/python3.15/site-packages"),
        ("4.0", "lib/python4.0/site-packages"),
    ],
)
def test_get_python_site_packages_short_path_unix(
    monkeypatch: pytest.MonkeyPatch, python_version: str, expected: str
):
    monkeypatch.setattr(python_path, "on_win", False)
    assert get_python_site_packages_short_path(python_version) == expected


@pytest.mark.parametrize(
    "python_version,expected",
    [
        ("2.7", "Lib/site-packages"),
        ("3.8", "Lib/site-packages"),
        ("3.14.2", "Lib/site-packages"),
        # Python 3.15+ on Windows uses lib/python/site-packages
        ("3.15", "lib/python/site-packages"),
        ("3.15.0", "lib/python/site-packages"),
        ("3.16", "lib/python/site-packages"),
        ("4.0", "lib/python/site-packages"),
        ("4.20.1", "lib/python/site-packages"),
        # Unparseable version falls back to the legacy layout
        ("3", "Lib/site-packages"),
    ],
)
def test_get_python_site_packages_short_path_windows(
    monkeypatch: pytest.MonkeyPatch, python_version: str, expected: str
):
    monkeypatch.setattr(python_path, "on_win", True)
    assert get_python_site_packages_short_path(python_version) == expected
