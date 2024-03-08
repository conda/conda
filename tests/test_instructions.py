# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
import os

import pytest

from conda import instructions
from conda.exceptions import CondaFileIOError
from conda.exports import execute_instructions
from conda.instructions import commands


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


def test_simple_instruction():
    index = {"This is an index": True}

    def simple_cmd(state, arg):
        simple_cmd.called = True
        simple_cmd.call_args = arg

    commands["SIMPLE"] = simple_cmd

    plan = [("SIMPLE", ["arg1"])]

    execute_instructions(plan, index, verbose=False)

    assert simple_cmd.called
    assert simple_cmd.call_args == ["arg1"]


def test_state():
    index = {"This is an index": True}

    def simple_cmd(state, arg):
        expect, x = arg
        state.setdefault("x", 1)
        assert state["x"] == expect
        state["x"] = x
        simple_cmd.called = True

    commands["SIMPLE"] = simple_cmd

    plan = [
        ("SIMPLE", (1, 5)),
        ("SIMPLE", (5, None)),
    ]

    execute_instructions(plan, index, verbose=False)
    assert simple_cmd.called


def test_check_files_in_tarball_files_exist():
    source_dir = os.getcwd()
    files = [__file__]
    assert instructions.check_files_in_package(source_dir, files)


def test_check_files_in_tarball_files_not_exist():
    source_dir = os.getcwd()
    files = ["test-thing-that-does-not-exist"]

    with pytest.raises(CondaFileIOError):
        instructions.check_files_in_package(source_dir, files)
