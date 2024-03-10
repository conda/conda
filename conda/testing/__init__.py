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

import json
import os
import sys
import uuid
import warnings
from contextlib import contextmanager, nullcontext
from dataclasses import dataclass
from logging import getLogger
from os.path import join
from pathlib import Path
from shutil import copyfile
from typing import TYPE_CHECKING, overload

import pytest

from ..auxlib.entity import EntityEncoder
from ..base.constants import PACKAGE_CACHE_MAGIC_FILE
from ..base.context import context, reset_context
from ..cli.main import main_subshell
from ..common.compat import on_win
from ..common.url import path_to_url
from ..core.package_cache_data import PackageCacheData
from ..deprecations import deprecated
from ..exceptions import CondaExitZero
from ..models.records import PackageRecord

if TYPE_CHECKING:
    from typing import Iterator

    from pytest import CaptureFixture, ExceptionInfo, MonkeyPatch
    from pytest_mock import MockerFixture

log = getLogger(__name__)


@deprecated(
    "24.9",
    "25.3",
    addendum="It don't matter which environment the test suite is run from.",
)
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
        from ..activate import CmdExeActivator, PosixActivator

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


@dataclass
class CondaCLIFixture:
    capsys: CaptureFixture

    @overload
    def __call__(
        self,
        *argv: str | os.PathLike | Path,
        raises: type[Exception] | tuple[type[Exception], ...],
    ) -> tuple[str, str, ExceptionInfo]:
        ...

    @overload
    def __call__(self, *argv: str | os.PathLike | Path) -> tuple[str, str, int]:
        ...

    def __call__(
        self,
        *argv: str | os.PathLike | Path,
        raises: type[Exception] | tuple[type[Exception], ...] | None = None,
    ) -> tuple[str, str, int | ExceptionInfo]:
        """Test conda CLI. Mimic what is done in `conda.cli.main.main`.

        `conda ...` == `conda_cli(...)`

        :param argv: Arguments to parse.
        :param raises: Expected exception to intercept. If provided, the raised exception
            will be returned instead of exit code (see pytest.raises and pytest.ExceptionInfo).
        :return: Command results (stdout, stderr, exit code or pytest.ExceptionInfo).
        """
        # clear output
        self.capsys.readouterr()

        # ensure arguments are string
        argv = tuple(map(str, argv))

        # run command
        code = None
        with pytest.raises(raises) if raises else nullcontext() as exception:
            code = main_subshell(*argv)
        # capture output
        out, err = self.capsys.readouterr()

        # restore to prior state
        reset_context()

        return out, err, exception if raises else code


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


@dataclass
class TmpChannelFixture:
    path_factory: PathFactoryFixture
    conda_cli: CondaCLIFixture

    @contextmanager
    def __call__(self, *packages: str) -> Iterator[tuple[Path, str]]:
        # download packages
        self.conda_cli(
            "create",
            f"--prefix={self.path_factory()}",
            *packages,
            "--yes",
            "--quiet",
            "--download-only",
            raises=CondaExitZero,
        )

        pkgs_dir = Path(PackageCacheData.first_writable().pkgs_dir)
        pkgs_cache = PackageCacheData(pkgs_dir)

        channel = self.path_factory()
        subdir = channel / context.subdir
        subdir.mkdir(parents=True)
        noarch = channel / "noarch"
        noarch.mkdir(parents=True)

        repodata = {"info": {}, "packages": {}}
        for package in packages:
            for pkg_data in pkgs_cache.query(package):
                fname = pkg_data["fn"]

                copyfile(pkgs_dir / fname, subdir / fname)

                repodata["packages"][fname] = PackageRecord(
                    **{
                        field: value
                        for field, value in pkg_data.dump().items()
                        if field not in ("url", "channel", "schannel")
                    }
                )

        (subdir / "repodata.json").write_text(json.dumps(repodata, cls=EntityEncoder))
        (noarch / "repodata.json").write_text(json.dumps({}, cls=EntityEncoder))

        for package in packages:
            assert any(PackageCacheData.query_all(package))

        yield channel, path_to_url(str(channel))


@pytest.fixture
def tmp_channel(
    path_factory: PathFactoryFixture,
    conda_cli: CondaCLIFixture,
) -> TmpChannelFixture:
    """Fixture returning TmpChannelFixture instance."""
    yield TmpChannelFixture(path_factory, conda_cli)


@pytest.fixture(name="monkeypatch")
def context_aware_monkeypatch(monkeypatch: MonkeyPatch) -> MonkeyPatch:
    """A monkeypatch fixture that resets context after each test"""
    yield monkeypatch

    # reset context if any CONDA_ variables were set/unset
    if conda_vars := [
        name
        for obj, name, _ in monkeypatch._setitem
        if obj is os.environ and name.startswith("CONDA_")
    ]:
        log.debug(f"monkeypatch cleanup: undo & reset context: {', '.join(conda_vars)}")
        monkeypatch.undo()
        # reload context without search paths
        reset_context([])


@pytest.fixture
def tmp_pkgs_dir(path_factory: PathFactoryFixture, mocker: MockerFixture) -> Path:
    pkgs_dir = path_factory() / "pkgs"
    pkgs_dir.mkdir(parents=True)
    (pkgs_dir / PACKAGE_CACHE_MAGIC_FILE).touch()

    mocker.patch(
        "conda.base.context.Context.pkgs_dirs",
        new_callable=mocker.PropertyMock,
        return_value=(pkgs_dir_str := str(pkgs_dir),),
    )
    assert context.pkgs_dirs == (pkgs_dir_str,)

    yield pkgs_dir

    PackageCacheData._cache_.pop(pkgs_dir_str, None)
