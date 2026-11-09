# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
from __future__ import annotations

import errno
import os
from contextlib import nullcontext
from typing import TYPE_CHECKING

import pytest

from conda.common.compat import on_win
from conda.exceptions import LinkSourceNotFoundError
from conda.gateways.disk import create
from conda.gateways.disk.create import create_link
from conda.gateways.disk.link import link
from conda.models.enums import LinkType

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


def test_create_link_missing_source_raises_link_source_not_found(tmp_path):
    src = str(tmp_path / "missing-source")
    dst = str(tmp_path / "destination")

    with pytest.raises(LinkSourceNotFoundError) as exc:
        create_link(src, dst, LinkType.softlink)

    assert exc.value.src == src


@pytest.mark.parametrize(
    "fallback_copy,raises",
    [
        pytest.param(True, False, id="fallback-to-copy"),
        pytest.param(False, True, id="raise-error"),
    ],
)
def test_create_hardlink_across_fs(mocker, tmp_path: Path, fallback_copy, raises):
    source = tmp_path / "pkgs" / "index.json"
    source.parent.mkdir()
    source.touch()
    dest_dir = tmp_path / "dest"
    dest_dir.mkdir()

    # simulate pkgs/ and env/ residing on different filesystems
    def cross_device_link(src, dst):
        if dst == dest_dir:
            raise OSError(errno.EXDEV, "Invalid cross-device link")
        return link(src, dst)

    mocker.patch("conda.gateways.disk.create.link", side_effect=cross_device_link)

    if raises:
        with pytest.raises(OSError):
            create_link(
                source,
                dest_dir,
                link_type=LinkType.hardlink,
                fallback_copy=fallback_copy,
            )
            assert not (dest_dir / "test-source").exists
    else:
        create_link(
            source, dest_dir, link_type=LinkType.hardlink, fallback_copy=fallback_copy
        )
        assert (dest_dir / "test-source").exists


@pytest.mark.skipif(on_win, reason="symlinks are copied as files on Windows")
@pytest.mark.parametrize(
    "absolute,target_is_dir,expected_symlink",
    [
        pytest.param(False, False, True, id="relative-file"),
        pytest.param(False, True, True, id="relative-directory"),
        pytest.param(True, False, False, id="absolute-file"),
        pytest.param(True, True, True, id="absolute-directory"),
    ],
)
def test_copy_symlink(
    tmp_path: Path, absolute: bool, target_is_dir: bool, expected_symlink: bool
) -> None:
    target = tmp_path / "target"
    if target_is_dir:
        target.mkdir()
    else:
        target.write_text("content")
    src = tmp_path / "src"
    link_target = str(target) if absolute else target.name
    src.symlink_to(link_target)
    dst = tmp_path / "dst"

    create.copy(str(src), str(dst))

    assert dst.is_symlink() == expected_symlink
    if expected_symlink:
        assert os.readlink(dst) == link_target
    if not target_is_dir:
        assert dst.read_text() == "content"
