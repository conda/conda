# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
# Attempt to move any conda entries in PATH to the front of it.
# IDEs have their own ideas about how PATH should be managed and
# they do dumb stuff like add /usr/bin to the front of it
# meaning conda takes a submissive role and the wrong stuff
# runs (when other conda prefixes get activated they replace
# the wrongly placed entries with newer wrongly placed entries).
#
# Note, there's still condabin to worry about here, and also should
# we not remove all traces of conda instead of just this fixup?
# Ideally we'd have two modes, 'removed' and 'fixed'. I have seen
# condabin come from an entirely different installation than
# CONDA_PREFIX too in some instances and that really needs fixing.
from __future__ import annotations

import os
import sys
import uuid
import warnings
from contextlib import contextmanager
from dataclasses import dataclass
from os.path import dirname, isfile, join, normpath
from pathlib import Path
from subprocess import check_output
from typing import Iterator

import pytest
from pytest import CaptureFixture

from conda.base.context import context, reset_context
from conda.cli.main import init_loggers
from conda.common.compat import on_win

from ..deprecations import deprecated


@deprecated("23.9", "24.3")
def encode_for_env_var(value) -> str:
    """Environment names and values need to be string."""
    if isinstance(value, str):
        return value
    elif isinstance(value, bytes):
        return value.decode()
    return str(value)


def conda_ensure_sys_python_is_base_env_python():
    # Exit if we try to run tests from a non-base env. The tests end up installing
    # menuinst into the env they are called with and that breaks non-base env activation
    # as it emits a message to stderr:
    # WARNING menuinst_win32:<module>(157): menuinst called from non-root env
    # C:\opt\conda\envs\py27
    # So lets just sys.exit on that.

    if "CONDA_PYTHON_EXE" in os.environ:
        if (
            Path(os.environ["CONDA_PYTHON_EXE"]).resolve()
            != Path(sys.executable).resolve()
        ):
            warnings.warn(
                "ERROR :: Running tests from a non-base Python interpreter. "
                " Tests requires installing menuinst and that causes stderr "
                " output when activated.\n"
                f"- CONDA_PYTHON_EXE={os.environ['CONDA_PYTHON_EXE']}\n"
                f"- sys.executable={sys.executable}"
            )

            # menuinst only really matters on windows
            if on_win:
                sys.exit(-1)


def conda_move_to_front_of_PATH():
    if "CONDA_PREFIX" in os.environ:
        from conda.activate import CmdExeActivator, PosixActivator

        if os.name == "nt":
            activator_cls = CmdExeActivator
        else:
            activator_cls = PosixActivator
        activator = activator_cls()
        # But why not just use _replace_prefix_in_path? => because moving
        # the entries to the front of PATH is the goal here, not swapping
        # x for x (which would be pointless anyway).
        p = None
        # It might be nice to have a parameterised fixture with choices of:
        # 'System default PATH',
        # 'IDE default PATH',
        # 'Fully activated conda',
        # 'PATHly activated conda'
        # This will do for now => Note, if you have conda activated multiple
        # times it could mask some test failures but _remove_prefix_from_path
        # cannot be used multiple times; it will only remove *one* conda
        # prefix from the *original* value of PATH, calling it N times will
        # just return the same value every time, even if you update PATH.
        p = activator._remove_prefix_from_path(os.environ["CONDA_PREFIX"])

        # Replace any non sys.prefix condabin with sys.prefix condabin
        new_p = []
        found_condabin = False
        for pe in p:
            if pe.endswith("condabin"):
                if not found_condabin:
                    found_condabin = True
                    if join(sys.prefix, "condabin") != pe:
                        condabin_path = join(sys.prefix, "condabin")
                        print(f"Incorrect condabin, swapping {pe} to {condabin_path}")
                        new_p.append(condabin_path)
                    else:
                        new_p.append(pe)
            else:
                new_p.append(pe)

        os.environ["PATH"] = os.pathsep.join(new_p)
        activator = activator_cls()
        p = activator._add_prefix_to_path(os.environ["CONDA_PREFIX"])
        os.environ["PATH"] = os.pathsep.join(p)


@deprecated(
    "23.9",
    "24.3",
    addendum="Unnecessary with transition to hatchling for build system.",
)
def conda_check_versions_aligned():
    # Next problem. If we use conda to provide our git or otherwise do not
    # have it on PATH and if we also have no .version file then conda is
    # unable to figure out its version without throwing an exception. The
    # tests this broke most badly (test_activate.py) have a workaround of
    # installing git into one of the conda prefixes that gets used but it
    # is slow. Instead write .version if it does not exist, and also fix
    # it if it disagrees.

    import conda

    version_file = normpath(join(dirname(conda.__file__), ".version"))
    if isfile(version_file):
        version_from_file = open(version_file).read().split("\n")[0]
    else:
        version_from_file = None

    git_exe = "git.exe" if sys.platform == "win32" else "git"
    version_from_git = None
    for pe in os.environ.get("PATH", "").split(os.pathsep):
        if isfile(join(pe, git_exe)):
            try:
                cmd = join(pe, git_exe) + " describe --tags --long"
                version_from_git = check_output(cmd).decode("utf-8").split("\n")[0]
                from conda.auxlib.packaging import _get_version_from_git_tag

                version_from_git = _get_version_from_git_tag(version_from_git)
                break
            except:
                continue
    if not version_from_git:
        print("WARNING :: Could not check versions.")

    if version_from_git and version_from_git != version_from_file:
        print(
            "WARNING :: conda/.version ({}) and git describe ({}) "
            "disagree, rewriting .version".format(version_from_git, version_from_file)
        )
        with open(version_file, "w") as fh:
            fh.write(version_from_git)


@dataclass
class CondaCLIFixture:
    capsys: CaptureFixture

    def __call__(self, *argv: str) -> tuple[str, str, int]:
        """Test conda CLI. Mimic what is done in `conda.cli.main.main`.

        `conda ...` == `conda_cli(...)`

        :param argv: Arguments to parse
        :return: Command results
        :rtype: tuple[stdout, stdout, exitcode]
        """
        # clear output
        self.capsys.readouterr()

        # ensure arguments are string
        argv = tuple(map(str, argv))

        # mock legacy subcommands
        if argv[0] == "env":
            from conda_env.cli.main import create_parser, do_call

            argv = argv[1:]

            # parse arguments
            parser = create_parser()
            args = parser.parse_args(argv)

            # initialize context and loggers
            context.__init__(argparse_args=args)
            init_loggers()

            # run command
            code = do_call(args, parser)

        # all other subcommands
        else:
            from conda.cli.main import main_subshell

            # run command
            code = main_subshell(*argv)

        # capture output
        out, err = self.capsys.readouterr()

        # restore to prior state
        reset_context()

        return out, err, code


@pytest.fixture
def conda_cli(capsys: CaptureFixture) -> CondaCLIFixture:
    """Fixture returning CondaCLIFixture instance."""
    yield CondaCLIFixture(capsys)


@dataclass
class PathFactoryFixture:
    tmp_path: Path

    def __call__(
        self,
        name: str | None = None,
        prefix: str | None = None,
        suffix: str | None = None,
    ) -> Path:
        """Unique, non-existent path factory.

        Extends pytest's `tmp_path` fixture with a new unique, non-existent path for usage in cases
        where we need a temporary path that doesn't exist yet.

        :param name: Path name to append to `tmp_path`
        :param prefix: Prefix to prepend to unique name generated
        :param suffix: Suffix to append to unique name generated
        :return: A new unique path
        """
        prefix = prefix or ""
        name = name or uuid.uuid4().hex
        suffix = suffix or ""
        return self.tmp_path / (prefix + name + suffix)


@pytest.fixture
def path_factory(tmp_path: Path) -> PathFactoryFixture:
    """Fixture returning PathFactoryFixture instance."""
    yield PathFactoryFixture(tmp_path)


@dataclass
class TmpEnvFixture:
    path_factory: PathFactoryFixture
    conda_cli: CondaCLIFixture

    @contextmanager
    def __call__(
        self,
        *packages: str,
        prefix: str | os.PathLike | None = None,
    ) -> Iterator[Path]:
        """Generate a conda environment with the provided packages.

        :param packages: The packages to install into environment
        :param prefix: The prefix at which to install the conda environment
        :return: The conda environment's prefix
        """
        prefix = Path(prefix or self.path_factory())

        reset_context([prefix / "condarc"])
        self.conda_cli("create", "--prefix", prefix, *packages, "--yes", "--quiet")
        yield prefix

        # no need to remove prefix since it is in a temporary directory


@pytest.fixture
def tmp_env(
    path_factory: PathFactoryFixture,
    conda_cli: CondaCLIFixture,
) -> TmpEnvFixture:
    """Fixture returning TmpEnvFixture instance."""
    yield TmpEnvFixture(path_factory, conda_cli)
