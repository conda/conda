# -*- coding: utf-8 -*-
# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause

from conda import utils
from conda.common.path import win_path_to_unix
from conda.testing.helpers import assert_equals

from conda.activate import CmdExeActivator, PosixActivator
from conda.common.path import which
from logging import getLogger
from os import environ, pathsep
from os.path import dirname, join
import sys
from conda.common.compat import on_win

import pytest


SOME_PREFIX = "/some/prefix"
SOME_FILES = ["a", "b", "c"]
log = getLogger(__name__)


def test_path_translations():
    paths = [
        (r"z:\miniconda\Scripts\pip.exe",
         "/z/miniconda/Scripts/pip.exe",
         "/cygdrive/z/miniconda/Scripts/pip.exe"),
        (r"z:\miniconda;z:\Documents (x86)\pip.exe;c:\test",
         "/z/miniconda:/z/Documents (x86)/pip.exe:/c/test",
         "/cygdrive/z/miniconda:/cygdrive/z/Documents (x86)/pip.exe:/cygdrive/c/test"),
        # Failures:
        # (r"z:\miniconda\Scripts\pip.exe",
        #  "/z/miniconda/Scripts/pip.exe",
        #  "/cygdrive/z/miniconda/Scripts/pip.exe"),

        # ("z:\\miniconda\\",
        #  "/z/miniconda/",
        #  "/cygdrive/z/miniconda/"),
        ("test dummy text /usr/bin;z:\\documents (x86)\\code\\conda\\tests\\envskhkzts\\test1;z:\\documents\\code\\conda\\tests\\envskhkzts\\test1\\cmd more dummy text",
        "test dummy text /usr/bin:/z/documents (x86)/code/conda/tests/envskhkzts/test1:/z/documents/code/conda/tests/envskhkzts/test1/cmd more dummy text",
        "test dummy text /usr/bin:/cygdrive/z/documents (x86)/code/conda/tests/envskhkzts/test1:/cygdrive/z/documents/code/conda/tests/envskhkzts/test1/cmd more dummy text"),
    ]
    for windows_path, unix_path, cygwin_path in paths:
        assert win_path_to_unix(windows_path) == unix_path
        assert utils.unix_path_to_win(unix_path) == windows_path

        # assert utils.win_path_to_cygwin(windows_path) == cygwin_path
        # assert utils.cygwin_path_to_win(cygwin_path) == windows_path


def test_text_translations():
    test_win_text = "z:\\msarahan\\code\\conda\\tests\\envsk5_b4i\\test 1"
    test_unix_text = "/z/msarahan/code/conda/tests/envsk5_b4i/test 1"
    assert_equals(test_win_text, utils.unix_path_to_win(test_unix_text))
    assert_equals(test_unix_text, win_path_to_unix(test_win_text))


def get_conda_prefixes_on_PATH():
    '''
    :return: A tuple of:
               A list of conda prefixes found on PATH in the order in which they appear.
               A list of the suffixes that determine a conda prefix on this platform.
    '''

    if on_win:
        condapathlist = list(CmdExeActivator()._get_path_dirs(''))
    else:
        condapathlist = list(PosixActivator()._get_path_dirs(''))
    pathlist=environ.get('PATH', '').split(pathsep)
    pathlist=pathlist+pathlist
    conda_prefixes = []
    for pei, _ in enumerate(pathlist[:-len(condapathlist)]):
        all_good = True
        for cei, ce in enumerate(condapathlist):
            if not pathlist[pei + cei].endswith(ce):
                all_good = False
                break
        if not all_good:
            continue
        conda_prefixes.append(pathlist[pei][-len(condapathlist[0]):])
    return conda_prefixes, condapathlist


def get_prefix_containing_test_programs(test_programs=()):
    '''
    This function returns the conda prefix of test_programs on PATH if:

    1. Conda's path entries are found on PATH in the correct order.
    2. The `test_programs` are *all* found to exist in that prefix (this is to catch
       stacked activation where the expected program is shadowed by the most recently
       pushed env. and also when expected programs are not installed. It also detects
       mixed scenarios where different programs come from different prefixes which is
       never what we want.
    '''

    prefixes, suffixes = get_conda_prefixes_on_PATH()
    for test_program in test_programs:
        test_program_on_path = which(test_program)
        if not test_program_on_path:
            log.warning("{} not found on PATH".format(test_program))
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
                    log.warning("{} not found in any conda prefixes ({}) on PATH", test_program, prefixes)
                    return None
            if len(set(test_program_in_prefix))!=1:
                log.warning("test_programs ({}) not all found in the same prefix".format(test_programs))
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


# Some stuff I was playing with, env_unmodified(conda_tests_ctxt_mgmt_def_pol)
# from contextlib import contextmanager
# from conda.base.constants import DEFAULT_CHANNELS
# from conda.base.context import context, reset_context, stack_context_default
# from conda.common.io import env_vars
# from conda.common.compat import odict
# from conda.common.configuration import YamlRawParameter
# from conda.common.serialize import yaml_safe_load
# from conda.models.channel import Channel
# from conda.testing.integration import make_temp_prefix
# from os.path import join
# from shutil import rmtree
# is what I ended up with instead.
#
# I do maintain however, that all of:
# env_{var,vars,unmodified} and make_temp_env must be combined into one function
#
# .. because as things stand, they are frequently nested but they can and do
# conflict with each other. For example make_temp_env calls reset_context()
# which will break our ContextStack (which is currently unused, but will be
# later I hope).

# @contextmanager
# def make_default_conda_config(env=dict({})):
#     prefix = make_temp_prefix()
#     condarc = join(prefix, 'condarc')
#     with open(condarc, 'w') as condarcf:
#         condarcf.write("default_channels:\n")
#         for c in list(DEFAULT_CHANNELS):
#             condarcf.write('  - ' + c + '\n')
#     if not env:
#         env2 = dict({'CONDARC': condarc})
#     else:
#         env2 = env.copy()
#         env2['CONDARC'] = condarc
#     with env_vars(env2, lambda: reset_context((condarc,))):
#         try:
#             yield condarc
#         finally:
#             rmtree(prefix, ignore_errors=True)
#             # Expensive and probably unnecessary?
#             reset_context()
#
#
# @contextmanager
# def make_default_conda_config(env=dict({})):
#     with env_vars(env, stack_context_default):
#         reset_context(())
#         rd = odict(testdata=YamlRawParameter.make_raw_parameters('testdata', yaml_safe_load('')))
#         context._set_raw_data(rd)
#         Channel._reset_state()
#         try:
#             yield None
#         finally:
#             pass
#
