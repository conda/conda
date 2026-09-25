# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
from __future__ import annotations

import os
from contextlib import nullcontext
from typing import TYPE_CHECKING

import pytest

from conda.common.compat import on_win
from conda.gateways.disk import create

if TYPE_CHECKING:
    from pathlib import Path


@pytest.mark.parametrize(
    "function,raises",
    [
        ("extract_tarball", TypeError),
    ],
)
def test_deprecations(function: str, raises: type[Exception] | None) -> None:
    raises_context = pytest.raises(raises) if raises else nullcontext()
    with pytest.deprecated_call(), raises_context:
        getattr(create, function)()


@pytest.mark.skipif(on_win, reason="symlinks are copied as files on Windows")
@pytest.mark.parametrize("target_is_dir", [True, False])
def test_copy_absolute_symlink(tmp_path: Path, target_is_dir: bool) -> None:
    target = tmp_path / "target"
    if target_is_dir:
        target.mkdir()
    else:
        target.write_text("content")
    src = tmp_path / "src"
    src.symlink_to(target)
    dst = tmp_path / "dst"

    create.copy(str(src), str(dst))

    # symlinks to directories are kept; symlinks to files are dereferenced
    assert dst.is_symlink() == target_is_dir
    if target_is_dir:
        assert os.readlink(dst) == str(target)
    else:
        assert dst.read_text() == "content"
