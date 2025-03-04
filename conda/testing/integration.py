# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""
These helpers were originally defined in tests/test_create.py,
but were refactored here so downstream projects can benefit from
them too.
"""

from __future__ import annotations

import os
import sys
from functools import cache
from logging import getLogger
from os.path import dirname, isdir, join
from pathlib import Path
from random import sample
from subprocess import check_output
from tempfile import gettempdir
from typing import TYPE_CHECKING
from uuid import uuid4

import pytest

from ..auxlib.compat import Utf8NamedTemporaryFile
from ..base.context import context, reset_context
from ..cli.conda_argparse import do_call, generate_parser
from ..cli.main import init_loggers
from ..common.compat import on_win
from ..common.io import (
    argv,
    captured,
    dashlist,
    stderr_log_level,
)
from ..common.path import BIN_DIRECTORY
from ..core.prefix_data import PrefixData
from ..deprecations import deprecated
from ..exceptions import conda_exception_handler
from ..gateways.disk.delete import rm_rf
from ..gateways.disk.link import link
from ..gateways.logging import DEBUG
from ..models.match_spec import MatchSpec
from ..utils import massage_arguments

if TYPE_CHECKING:
    from ..models.records import PrefixRecord

TEST_LOG_LEVEL = DEBUG
PYTHON_BINARY = "python.exe" if on_win else "bin/python"
deprecated.constant(
    "25.3",
    "25.9",
    "BIN_DIRECTORY",
    BIN_DIRECTORY,
    addendum="Use `conda.common.path.BIN_DIRECTORY` instead.",
)
del BIN_DIRECTORY
UNICODE_CHARACTERS = "ōγђ家固한áêñßôç"
# UNICODE_CHARACTERS_RESTRICTED = u"áêñßôç"
UNICODE_CHARACTERS_RESTRICTED = "abcdef"
which_or_where = "which" if not on_win else "where"
cp_or_copy = "cp" if not on_win else "copy"
env_or_set = "env" if not on_win else "set"

# UNICODE_CHARACTERS = u"12345678abcdef"
# UNICODE_CHARACTERS_RESTRICTED = UNICODE_CHARACTERS

# When testing for bugs, you may want to change this to a _,
# for example to see if a bug is related to spaces in prefixes.
SPACER_CHARACTER = " "

log = getLogger(__name__)


def escape_for_winpath(p):
    return p.replace("\\", "\\\\")


@cache
@deprecated("24.9", "25.3")
def running_a_python_capable_of_unicode_subprocessing():
    name = None
    # try:
    # UNICODE_CHARACTERS + os.sep +
    with Utf8NamedTemporaryFile(
        mode="w", suffix=UNICODE_CHARACTERS + ".bat", delete=False
    ) as batch_file:
        batch_file.write("@echo Hello World\n")
        batch_file.write("@exit 0\n")
        name = batch_file.name
    if name:
        try:
            out = check_output(name, cwd=dirname(name), stderr=None, shell=False)
            out = out.decode("utf-8") if hasattr(out, "decode") else out
            if out.startswith("Hello World"):
                return True
            return False
        except Exception:
            return False
        finally:
            os.unlink(name)
    return False


tmpdir_in_use = None


@pytest.fixture(autouse=True)
@deprecated(
    "24.9",
    "25.3",
    addendum="Use `tmp_path`, `conda.testing.path_factory`, or `conda.testing.tmp_env` instead.",
)
def set_tmpdir(tmpdir):
    global tmpdir_in_use
    if not tmpdir:
        return tmpdir_in_use
    td = tmpdir.strpath
    assert os.sep in td
    tmpdir_in_use = td


@deprecated(
    "24.9",
    "25.3",
    addendum="Use `tmp_path`, `conda.testing.path_factory`, or `conda.testing.tmp_env` instead.",
)
def _get_temp_prefix(name=None, use_restricted_unicode=False):
    tmpdir = tmpdir_in_use or gettempdir()
    capable = running_a_python_capable_of_unicode_subprocessing()

    if not capable or use_restricted_unicode:
        RESTRICTED = UNICODE_CHARACTERS_RESTRICTED
        random_unicode = "".join(sample(RESTRICTED, len(RESTRICTED)))
    else:
        random_unicode = "".join(sample(UNICODE_CHARACTERS, len(UNICODE_CHARACTERS)))
    tmpdir_name = os.environ.get(
        "CONDA_TEST_TMPDIR_NAME",
        (str(uuid4())[:4] + SPACER_CHARACTER + random_unicode)
        if name is None
        else name,
    )
    prefix = join(tmpdir, tmpdir_name)

    # Exit immediately if we cannot use hardlinks, on Windows, we get permissions errors if we use
    # sys.executable so instead use the pdb files.
    src = sys.executable.replace(".exe", ".pdb") if on_win else sys.executable
    dst = os.path.join(tmpdir, os.path.basename(sys.executable))

    try:
        link(src, dst)
    except OSError:
        print(
            f"\nWARNING :: You are testing `conda` with `tmpdir`:-\n           {tmpdir}\n"
            f"           not on the same FS as `sys.prefix`:\n           {sys.prefix}\n"
            "           this will be slow and unlike the majority of end-user installs.\n"
            "           Please pass `--basetemp=<somewhere-else>` instead."
        )
    try:
        rm_rf(dst)
    except Exception as e:
        print(e)
        pass

    return prefix


@deprecated(
    "24.9",
    "25.3",
    addendum="Use `tmp_path`, `conda.testing.path_factory`, or `conda.testing.tmp_env` instead.",
)
def make_temp_prefix(name=None, use_restricted_unicode=False, _temp_prefix=None):
    """
    When the env. you are creating will be used to install Python 2.7 on Windows
    only a restricted amount of Unicode will work, and probably only those chars
    in your current codepage, so the characters in UNICODE_CHARACTERS_RESTRICTED
    should probably be randomly generated from that instead. The problem here is
    that the current codepage needs to be able to handle 'sys.prefix' otherwise
    ntpath will fall over.
    """
    if not _temp_prefix:
        _temp_prefix = _get_temp_prefix(
            name=name, use_restricted_unicode=use_restricted_unicode
        )
    try:
        os.makedirs(_temp_prefix)
    except:
        pass
    assert isdir(_temp_prefix)
    return _temp_prefix


class Commands:
    COMPARE = "compare"
    CONFIG = "config"
    CLEAN = "clean"
    CREATE = "create"
    INFO = "info"
    INSTALL = "install"
    LIST = "list"
    REMOVE = "remove"
    SEARCH = "search"
    UPDATE = "update"
    RUN = "run"


@deprecated("23.9", "25.3", addendum="Use `conda.testing.conda_cli` instead.")
def run_command(command, prefix, *arguments, **kwargs) -> tuple[str, str, int]:
    assert isinstance(arguments, tuple), "run_command() arguments must be tuples"
    arguments = massage_arguments(arguments)

    use_exception_handler = kwargs.get("use_exception_handler", False)
    # These commands require 'dev' mode to be enabled during testing because
    # they end up calling run_script() in link.py and that uses wrapper scripts for e.g. activate.
    # Setting `dev` means that, in these scripts, conda is executed via:
    #   `sys.prefix/bin/python -m conda` (or the Windows equivalent).
    # .. and the source code for `conda` is put on `sys.path` via `PYTHONPATH` (a bit gross but
    # less so than always requiring `cwd` to be the root of the conda source tree in every case).
    # If you do not want this to happen for some test you must pass dev=False as a kwarg, though
    # for nearly all tests, you want to make sure you are running *this* conda and not some old
    # conda (it was random which you'd get depending on the initial values of PATH and PYTHONPATH
    # - and likely more variables - before `dev` came along). Setting CONDA_EXE is not enough
    # either because in the 4.5 days that would just run whatever Python was found first on PATH.
    command_defaults_to_dev = command in (
        Commands.CREATE,
        Commands.INSTALL,
        Commands.REMOVE,
        Commands.RUN,
    )
    dev = kwargs.get("dev", True if command_defaults_to_dev else False)
    debug = kwargs.get("debug_wrapper_scripts", False)

    p = generate_parser()

    if command is Commands.CONFIG:
        arguments.append("--file")
        arguments.append(join(prefix, "condarc"))
    if command in (
        Commands.LIST,
        Commands.COMPARE,
        Commands.CREATE,
        Commands.INSTALL,
        Commands.REMOVE,
        Commands.UPDATE,
        Commands.RUN,
    ):
        arguments.insert(0, "-p")
        arguments.insert(1, prefix)
    if command in (Commands.CREATE, Commands.INSTALL, Commands.REMOVE, Commands.UPDATE):
        arguments.extend(["-y", "-q"])

    arguments.insert(0, command)
    if dev:
        arguments.insert(1, "--dev")
    if debug:
        arguments.insert(1, "--debug-wrapper-scripts")

    # It would be nice at this point to re-use:
    # from ..cli.python_api import run_command as python_api_run_command
    # python_api_run_command
    # .. but that does not support no_capture and probably more stuff.

    args = p.parse_args(arguments)
    context._set_argparse_args(args)
    init_loggers()
    cap_args = () if not kwargs.get("no_capture") else (None, None)
    # list2cmdline is not exact, but it is only informational.
    print(
        "\n\nEXECUTING COMMAND >>> $ conda {}\n\n".format(" ".join(arguments)),
        file=sys.stderr,
    )
    with (
        stderr_log_level(TEST_LOG_LEVEL, "conda"),
        stderr_log_level(TEST_LOG_LEVEL, "requests"),
    ):
        with argv(["python_api", *arguments]), captured(*cap_args) as c:
            if use_exception_handler:
                result = conda_exception_handler(do_call, args, p)
            else:
                result = do_call(args, p)
        stdout = c.stdout
        stderr = c.stderr
        print(stdout, file=sys.stdout)
        print(stderr, file=sys.stderr)

    # Unfortunately there are other ways to change context, such as Commands.CREATE --offline.
    # You will probably end up playing whack-a-bug here adding more and more the tuple here.
    if command in (Commands.CONFIG,):
        reset_context([os.path.join(prefix + os.sep, "condarc")], args)
    return stdout, stderr, result


def package_is_installed(
    prefix: str | os.PathLike | Path,
    spec: str | MatchSpec,
) -> PrefixRecord | None:
    spec = MatchSpec(spec)
    prefix_recs = tuple(PrefixData(str(prefix), pip_interop_enabled=True).query(spec))
    if not prefix_recs:
        return None
    elif len(prefix_recs) > 1:
        raise AssertionError(
            f"Multiple packages installed.{dashlist(prec.dist_str() for prec in prefix_recs)}"
        )
    else:
        return prefix_recs[0]


def get_shortcut_dir(prefix_for_unix=sys.prefix):
    if sys.platform == "win32":
        # On Windows, .nonadmin has been historically created by constructor in sys.prefix
        user_mode = "user" if Path(sys.prefix, ".nonadmin").is_file() else "system"
        try:  # menuinst v2
            from menuinst.platforms.win_utils.knownfolders import dirs_src

            return dirs_src[user_mode]["start"][0]
        except ImportError:  # older menuinst versions; TODO: remove
            try:
                from menuinst.win32 import dirs_src

                return dirs_src[user_mode]["start"][0]
            except ImportError:
                from menuinst.win32 import dirs

                return dirs[user_mode]["start"]
    # on unix, .nonadmin is only created by menuinst v2 as needed on the target prefix
    # it might exist, or might not; if it doesn't, we try to create it
    # see https://github.com/conda/menuinst/issues/150
    non_admin_file = Path(prefix_for_unix, ".nonadmin")
    if non_admin_file.is_file():
        user_mode = "user"
    else:
        try:
            non_admin_file.touch()
        except OSError:
            user_mode = "system"
        else:
            user_mode = "user"
            non_admin_file.unlink()

    if sys.platform == "darwin":
        if user_mode == "user":
            return join(os.environ["HOME"], "Applications")
        return "/Applications"
    if sys.platform == "linux":
        if user_mode == "user":
            return join(os.environ["HOME"], ".local", "share", "applications")
        return "/usr/share/applications"
    raise NotImplementedError(sys.platform)
