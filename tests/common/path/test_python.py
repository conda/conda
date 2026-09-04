# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
from __future__ import annotations

import pytest

from conda.common.path.python import is_valid_import_path


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
