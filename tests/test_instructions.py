# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
import os

import pytest

from conda import instructions
from conda.exceptions import CondaFileIOError


def test_expected_operation_order():
    """Ensure expected order of operations"""
    expected = (
        instructions.CHECK_FETCH,
        instructions.FETCH,
        instructions.CHECK_EXTRACT,
        instructions.EXTRACT,
        instructions.UNLINK,
        instructions.LINK,
        instructions.SYMLINK_CONDA,
        instructions.RM_EXTRACTED,
        instructions.RM_FETCHED,
    )
    assert expected == instructions.ACTION_CODES


def test_check_files_in_tarball_files_exist():
    source_dir = os.getcwd()
    files = [__file__]
    assert instructions.check_files_in_package(source_dir, files)


def test_check_files_in_tarball_files_not_exist():
    source_dir = os.getcwd()
    files = ["test-thing-that-does-not-exist"]

    with pytest.raises(CondaFileIOError):
        instructions.check_files_in_package(source_dir, files)
