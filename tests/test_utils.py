# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
from __future__ import annotations

import sys
from contextlib import nullcontext
from logging import getLogger
from os import environ, pathsep
from os.path import dirname, join
from pathlib import Path
from shutil import which
from unittest.mock import patch

import pytest

from conda import CondaError, utils
from conda.activate import CmdExeActivator, PosixActivator
from conda.common.compat import on_win
from conda.common.path import (
    unix_path_to_win,
    win_path_to_unix,
)

SOME_PREFIX = "/some/prefix"
SOME_FILES = ["a", "b", "c"]
log = getLogger(__name__)


@pytest.mark.parametrize(
    "windows_path,unix_path",
    [
        (
            "Z:\\miniconda\\Scripts\\pip.exe",
            "/z/miniconda/Scripts/pip.exe",
        ),
        (
            "Z:\\miniconda;Z:\\Documents (x86)\\pip.exe;C:\\test",
            "/z/miniconda:/z/Documents (x86)/pip.exe:/c/test",
        ),
        (
            "Z:\\miniconda",
            "/z/miniconda",
        ),
        (
            "test dummy text \\usr\\bin;Z:\\documents (x86)\\code\\conda\\tests\\envskhkzts\\test1;Z:\\documents\\code\\conda\\tests\\envskhkzts\\test1\\cmd more dummy text",
            "test dummy text /usr/bin:/z/documents (x86)/code/conda/tests/envskhkzts/test1:/z/documents/code/conda/tests/envskhkzts/test1/cmd more dummy text",
        ),
        (
            "Z:\\user\\code\\conda\\tests\\test 1",
            "/z/user/code/conda/tests/test 1",
        ),
    ],
)
def test_path_translations(windows_path: str, unix_path: str) -> None:
    assert win_path_to_unix(windows_path) == unix_path
    assert unix_path_to_win(unix_path) == windows_path


def get_conda_prefixes_on_PATH():
    """
    :return: A tuple of:
               A list of conda prefixes found on PATH in the order in which they appear.
               A list of the suffixes that determine a conda prefix on this platform.
    """

    if on_win:
        condapathlist = list(CmdExeActivator()._get_path_dirs(""))
    else:
        condapathlist = list(PosixActivator()._get_path_dirs(""))
    pathlist = environ.get("PATH", "").split(pathsep)
    pathlist = pathlist + pathlist
    conda_prefixes = []
    for pei, _ in enumerate(pathlist[: -len(condapathlist)]):
        all_good = True
        for cei, ce in enumerate(condapathlist):
            if not pathlist[pei + cei].endswith(ce):
                all_good = False
                break
        if not all_good:
            continue
        conda_prefixes.append(pathlist[pei][-len(condapathlist[0]) :])
    return conda_prefixes, condapathlist


def get_prefix_containing_test_programs(test_programs=()):
    """
    This function returns the conda prefix of test_programs on PATH if:

    1. Conda's path entries are found on PATH in the correct order.
    2. The `test_programs` are *all* found to exist in that prefix (this is to catch
       stacked activation where the expected program is shadowed by the most recently
       pushed env. and also when expected programs are not installed. It also detects
       mixed scenarios where different programs come from different prefixes which is
       never what we want.
    """

    prefixes, suffixes = get_conda_prefixes_on_PATH()
    for test_program in test_programs:
        test_program_on_path = which(test_program)
        if not test_program_on_path:
            log.warning(f"{test_program} not found on PATH")
            return None
        else:
            test_program_in_prefix = []
            test_program_dir = dirname(test_program_on_path)
            found = False
            for pi, prefix in enumerate(prefixes):
                for suffix in suffixes:
                    if test_program_dir == join(prefix, suffix):
                        test_program_in_prefix.append(pi)
                        found = True
                        break
                if not found:
                    log.warning(
                        "{} not found in any conda prefixes ({}) on PATH",
                        test_program,
                        prefixes,
                    )
                    return None
            if len(set(test_program_in_prefix)) != 1:
                log.warning(
                    f"test_programs ({test_programs}) not all found in the same prefix"
                )
                return None
            return prefixes[test_program_in_prefix[0]]
    return prefixes[0] if prefixes else None


def is_prefix_activated_PATHwise(prefix=sys.prefix, test_programs=()):
    found_in = get_prefix_containing_test_programs(test_programs)
    if found_in and found_in == prefix:
        return True
    return False


mark_posix_only = pytest.mark.skipif(on_win, reason="POSIX only")
mark_win_only = pytest.mark.skipif(not on_win, reason="Windows only")

_posix_quotes = "'{}'".format
_win_quotes = '"{}"'.format
_quotes = _win_quotes if on_win else _posix_quotes


@pytest.mark.parametrize(
    ["args", "expected"],
    [
        pytest.param("arg1", "arg1"),
        pytest.param("arg1 and 2", _quotes("arg1 and 2")),
        pytest.param("arg1\nand\n2", _quotes("arg1\nand\n2")),
        pytest.param("numpy<1.22", _quotes("numpy<1.22")),
        pytest.param("numpy>=1.0", _quotes("numpy>=1.0")),
        pytest.param("one|two", _quotes("one|two")),
        pytest.param(">/dev/null", _quotes(">/dev/null")),
        pytest.param(">NUL", _quotes(">NUL")),
        pytest.param("1>/dev/null", _quotes("1>/dev/null")),
        pytest.param("1>NUL", _quotes("1>NUL")),
        pytest.param("2>/dev/null", _quotes("2>/dev/null")),
        pytest.param("2>NUL", _quotes("2>NUL")),
        pytest.param("2>&1", _quotes("2>&1")),
        pytest.param(None, _quotes("")),
        pytest.param(
            'malicious argument\\"&whoami',
            '"malicious argument\\""&whoami"',
            marks=mark_win_only,
        ),
        pytest.param(
            "C:\\temp\\some ^%file^% > nul",
            '"C:\\temp\\some ^%%file^%% > nul"',
            marks=mark_win_only,
        ),
        pytest.param("!", "!" if on_win else "'!'"),
        pytest.param("#", "#" if on_win else "'#'"),
        pytest.param("$", "$" if on_win else "'$'"),
        pytest.param("%", '"%%"' if on_win else "%"),
        pytest.param("&", _quotes("&")),
        pytest.param("'", "'" if on_win else "''\"'\"''"),
        pytest.param("(", "(" if on_win else "'('"),
        pytest.param(")", ")" if on_win else "')'"),
        pytest.param("*", "*" if on_win else "'*'"),
        pytest.param("+", "+"),
        pytest.param(",", ","),
        pytest.param("-", "-"),
        pytest.param(".", "."),
        pytest.param("/", "/"),
        pytest.param(":", ":"),
        pytest.param(";", ";" if on_win else "';'"),
        pytest.param("<", _quotes("<")),
        pytest.param("=", "="),
        pytest.param(">", _quotes(">")),
        pytest.param("?", "?" if on_win else "'?'"),
        pytest.param("@", "@"),
        pytest.param("[", "[" if on_win else "'['"),
        pytest.param("\\", "\\" if on_win else "'\\'"),
        pytest.param("]", "]" if on_win else "']'"),
        pytest.param("^", _quotes("^")),
        pytest.param("{", "{" if on_win else "'{'"),
        pytest.param("|", _quotes("|")),
        pytest.param("}", "}" if on_win else "'}'"),
        pytest.param("~", "~" if on_win else "'~'"),
        pytest.param('"', '""""' if on_win else "'\"'"),
    ],
)
def test_quote_for_shell(args, expected):
    assert utils.quote_for_shell(args) == expected


def test_ensure_dir(tmpdir):
    """Ensures that this decorator creates a directory."""
    new_dir = "test_dir"

    @utils.ensure_dir_exists
    def get_test_dir() -> Path:
        return Path(tmpdir).joinpath(new_dir)

    new_dir = get_test_dir()

    assert new_dir.is_dir()


def test_ensure_dir_errors():
    """Test to ensure correct error handling."""
    new_dir = "test_dir"
    exc_message = "Test!"

    with patch("pathlib.Path.mkdir") as mock_mkdir:
        mock_mkdir.side_effect = OSError(exc_message)

        @utils.ensure_dir_exists
        def get_test_dir() -> Path:
            test_dir = Path(new_dir)
            return test_dir

        with pytest.raises(CondaError) as exc_info:
            get_test_dir()

    assert exc_message in str(exc_info.value)


@pytest.mark.parametrize(
    "function,raises",
    [
        ("unix_shell_base", TypeError),
        ("msys2_shell_base", TypeError),
        ("shells", TypeError),
        ("win_path_to_cygwin", TypeError),
        ("cygwin_path_to_win", TypeError),
        ("translate_stream", TypeError),
        ("path_identity", TypeError),
        ("unix_path_to_win", TypeError),
    ],
)
def test_deprecations(function: str, raises: type[Exception] | None) -> None:
    raises_context = pytest.raises(raises) if raises else nullcontext()
    with pytest.deprecated_call(), raises_context:
        getattr(utils, function)()
