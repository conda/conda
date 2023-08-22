# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
import os
from os.path import exists, isfile, join, lexists
from pathlib import Path

import pytest

from conda.common.compat import on_win
from conda.gateways.disk.link import islink, link, readlink, symlink
from conda.gateways.disk.test import softlink_supported
from conda.gateways.disk.update import touch


def test_hard_link(tmp_path: Path):
    path1_real_file = join(tmp_path, "path1_real_file")
    path2_second_inode = join(tmp_path, "path2_second_inode")
    touch(path1_real_file)
    assert isfile(path1_real_file)
    assert not islink(path1_real_file)
    link(path1_real_file, path2_second_inode)
    assert isfile(path2_second_inode)
    assert not islink(path2_second_inode)

    path1_stat = os.lstat(path1_real_file)
    path2_stat = os.lstat(path2_second_inode)
    assert path1_stat.st_ino == path2_stat.st_ino
    assert path1_stat.st_nlink == path2_stat.st_nlink

    os.unlink(path2_second_inode)
    assert not lexists(path2_second_inode)
    assert os.lstat(path1_real_file).st_nlink == 1

    os.unlink(path1_real_file)
    assert not lexists(path1_real_file)


def test_soft_link(tmp_path: Path):
    path1_real_file = join(tmp_path, "path1_real_file")
    path2_symlink = join(tmp_path, "path2_symlink")
    touch(path1_real_file)
    assert isfile(path1_real_file)
    assert not islink(path1_real_file)

    if not softlink_supported(path1_real_file, tmp_path) and on_win:
        pytest.skip("softlink not supported")

    symlink(path1_real_file, path2_symlink)
    assert exists(path2_symlink)
    assert lexists(path2_symlink)
    assert islink(path2_symlink)

    assert readlink(path2_symlink).endswith(path1_real_file)
    # Windows Python >3.7, readlink actually gives something that starts with \\?\
    # \\?\C:\users\appveyor\appdata\local\temp\1\c571cb0c\path1_real_file

    assert os.lstat(path1_real_file).st_nlink == os.lstat(path2_symlink).st_nlink == 1

    os.unlink(path1_real_file)
    assert not isfile(path1_real_file)
    assert not lexists(path1_real_file)
    assert not exists(path1_real_file)
    assert lexists(path2_symlink)
    assert not exists(path2_symlink)

    os.unlink(path2_symlink)
    assert not lexists(path2_symlink)
    assert not exists(path2_symlink)
