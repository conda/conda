# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""Collection of pytest fixtures used in conda tests."""

from __future__ import annotations

import os
import subprocess
import uuid
import warnings
from contextlib import contextmanager, nullcontext
from dataclasses import dataclass
from itertools import chain
from logging import getLogger
from pathlib import Path
from shutil import copyfile
from typing import TYPE_CHECKING, Literal, TypeVar, overload

import py
import pytest

from conda.deprecations import deprecated

from .. import CONDA_SOURCE_ROOT
from ..auxlib.ish import dals
from ..base.constants import PACKAGE_CACHE_MAGIC_FILE
from ..base.context import conda_tests_ctxt_mgmt_def_pol, context, reset_context
from ..cli.main import main_subshell
from ..common.configuration import YamlRawParameter
from ..common.io import env_vars
from ..common.serialize import json, yaml_round_trip_load
from ..common.url import path_to_url
from ..core.package_cache_data import PackageCacheData
from ..core.subdir_data import SubdirData
from ..exceptions import CondaExitZero
from ..gateways.disk.create import TemporaryDirectory
from ..models.records import PackageRecord
from .integration import PYTHON_BINARY

if TYPE_CHECKING:
    from collections.abc import Iterable, Iterator

    from _pytest.capture import MultiCapture
    from pytest import (
        CaptureFixture,
        ExceptionInfo,
        FixtureRequest,
        MonkeyPatch,
        TempPathFactory,
    )
    from pytest_mock import MockerFixture

    from ..common.path import PathType


log = getLogger(__name__)


TEST_CONDARC = dals(
    """
    custom_channels:
      darwin: https://some.url.somewhere/stuff
      chuck: http://another.url:8080/with/path
    custom_multichannels:
      michele:
        - https://do.it.with/passion
        - learn_from_every_thing
      steve:
        - more-downloads
    channel_settings:
      - channel: darwin
        param_one: value_one
        param_two: value_two
      - channel: "http://localhost"
        param_one: value_one
        param_two: value_two
    migrated_custom_channels:
      darwin: s3://just/cant
      chuck: file:///var/lib/repo/
    migrated_channel_aliases:
      - https://conda.anaconda.org
    channel_alias: ftp://new.url:8082
    conda-build:
      root-dir: /some/test/path
    proxy_servers:
      http: http://user:pass@corp.com:8080
      https: none
      ftp:
      sftp: ''
      ftps: false
      rsync: 'false'
    aggressive_update_packages: []
    channel_priority: false
    """
)


@pytest.fixture(autouse=True)
def suppress_resource_warning():
    """
    Suppress `Unclosed Socket Warning`

    It seems urllib3 keeps a socket open to avoid costly recreation costs.

    xref: https://github.com/kennethreitz/requests/issues/1882
    """
    warnings.filterwarnings("ignore", category=ResourceWarning)


@pytest.fixture(scope="function")
def tmpdir(tmpdir, request):
    tmpdir = TemporaryDirectory(dir=str(tmpdir))
    request.addfinalizer(tmpdir.cleanup)
    return py.path.local(tmpdir.name)


@pytest.fixture(autouse=True)
def clear_subdir_cache():
    SubdirData.clear_cached_local_channel_data()


@pytest.fixture(scope="function")
def reset_conda_context():
    """Resets the context object after each test function is run."""
    yield

    reset_context()


@pytest.fixture()
def temp_package_cache(tmp_path_factory):
    """
    Used to isolate package or index cache from other tests.
    """
    pkgs_dir = tmp_path_factory.mktemp("pkgs")
    with env_vars(
        {"CONDA_PKGS_DIRS": str(pkgs_dir)}, stack_callback=conda_tests_ctxt_mgmt_def_pol
    ):
        yield pkgs_dir


@pytest.fixture(
    # allow CI to set the solver backends via the CONDA_TEST_SOLVERS env var
    params=os.environ.get("CONDA_TEST_SOLVERS", "libmamba,classic").split(",")
)
def parametrized_solver_fixture(
    request: FixtureRequest,
    monkeypatch: MonkeyPatch,
) -> Iterable[Literal["libmamba", "classic"]]:
    """
    A parameterized fixture that sets the solver backend to (1) libmamba
    and (2) classic for each test. It's using autouse=True, so only import it in
    modules that actually need it.

    Note that skips and xfails need to be done _inside_ the test body.
    Decorators can't be used because they are evaluated before the
    fixture has done its work!

    So, instead of:

        @pytest.mark.skipif(context.solver == "libmamba", reason="...")
        def test_foo():
            ...

    Do:

        def test_foo():
            if context.solver == "libmamba":
                pytest.skip("...")
            ...
    """
    yield from _solver_helper(request, monkeypatch, request.param)


@pytest.fixture
def solver_classic(
    request: FixtureRequest,
    monkeypatch: MonkeyPatch,
) -> Iterable[Literal["classic"]]:
    yield from _solver_helper(request, monkeypatch, "classic")


@pytest.fixture
def solver_libmamba(
    request: FixtureRequest,
    monkeypatch: MonkeyPatch,
) -> Iterable[Literal["libmamba"]]:
    yield from _solver_helper(request, monkeypatch, "libmamba")


Solver = TypeVar("Solver", Literal["libmamba"], Literal["classic"])


def _solver_helper(
    request: FixtureRequest,
    monkeypatch: MonkeyPatch,
    solver: Solver,
) -> Iterable[Solver]:
    # clear cached solver backends before & after each test
    context.plugin_manager.get_cached_solver_backend.cache_clear()
    request.addfinalizer(context.plugin_manager.get_cached_solver_backend.cache_clear)

    monkeypatch.setenv("CONDA_SOLVER", solver)
    reset_context()
    assert context.solver == solver

    yield solver


@pytest.fixture(scope="session")
@deprecated("25.9", "26.3")
def session_capsys(request) -> Iterator[MultiCapture]:
    # https://github.com/pytest-dev/pytest/issues/2704#issuecomment-603387680
    capmanager = request.config.pluginmanager.getplugin("capturemanager")
    with capmanager.global_and_fixture_disabled():
        yield capmanager._global_capturing


@dataclass
class CondaCLIFixture:
    capsys: CaptureFixture | None

    @overload
    def __call__(
        self,
        *argv: PathType,
        raises: type[Exception] | tuple[type[Exception], ...],
    ) -> tuple[str, str, ExceptionInfo]: ...

    @overload
    def __call__(
        self,
        *argv: PathType,
    ) -> tuple[str, str, int]: ...

    def __call__(
        self,
        *argv: PathType,
        raises: type[Exception] | tuple[type[Exception], ...] | None = None,
    ) -> tuple[str | None, str | None, int | ExceptionInfo]:
        """Test conda CLI. Mimic what is done in `conda.cli.main.main`.

        `conda ...` == `conda_cli(...)`

        :param argv: Arguments to parse.
        :param raises: Expected exception to intercept. If provided, the raised exception
            will be returned instead of exit code (see pytest.raises and pytest.ExceptionInfo).
        :return: Command results (stdout, stderr, exit code or pytest.ExceptionInfo).
        """
        # clear output
        if self.capsys:
            self.capsys.readouterr()

        # run command
        code = None
        with pytest.raises(raises) if raises else nullcontext() as exception:
            code = main_subshell(*self._cast_args(argv))
        # capture output
        if self.capsys:
            out, err = self.capsys.readouterr()
        else:
            out = err = None

        # restore to prior state
        reset_context()

        return out, err, exception if raises else code

    @staticmethod
    def _cast_args(argv: tuple[PathType, ...]) -> Iterable[str]:
        """Cast args to string and inspect for `conda run`.

        `conda run` is a unique case that requires `--dev` to use the src shell scripts
        and not the shell scripts provided by the installer.
        """
        # TODO: Refactor this so we don't expose testing infrastructure to the user
        # (i.e., deprecate `conda run --dev`).
        argv = map(str, argv)
        for arg in argv:
            yield arg

            # detect if arg is the command (the first positional)
            if arg[0] != "-":
                # this is the first positional, return remaining arguments

                # if this happens to be the `conda run` command, add --dev
                if arg == "run":
                    yield "--dev"  # use src, not installer's shell scripts

                yield from argv


@pytest.fixture
def conda_cli(capsys: CaptureFixture) -> Iterator[CondaCLIFixture]:
    """A function scoped fixture returning CondaCLIFixture instance.

    Use this for any commands that are local to the current test (e.g., creating a
    conda environment only used in the test).
    """
    yield CondaCLIFixture(capsys)


@pytest.fixture(scope="session")
def session_conda_cli() -> Iterator[CondaCLIFixture]:
    """A session scoped fixture returning CondaCLIFixture instance.

    Use this for any commands that are global to the test session (e.g., creating a
    conda environment shared across tests, `conda info`, etc.).
    """
    yield CondaCLIFixture(None)


@dataclass
class PipCLIFixture:
    """Fixture for calling pip in specific conda environments."""

    @overload
    def __call__(
        self,
        *argv: PathType,
        prefix: PathType,
        raises: type[Exception] | tuple[type[Exception], ...],
    ) -> tuple[str, str, ExceptionInfo]: ...

    @overload
    def __call__(
        self,
        *argv: PathType,
        prefix: PathType,
    ) -> tuple[str, str, int]: ...

    def __call__(
        self,
        *argv: PathType,
        prefix: PathType,
        raises: type[Exception] | tuple[type[Exception], ...] | None = None,
    ) -> tuple[str | None, str | None, int | ExceptionInfo]:
        """Test pip CLI in a specific conda environment.

        `pip ...` in environment == `pip_cli(..., prefix=env_path)`

        :param argv: Arguments to pass to pip.
        :param prefix: Path to the conda environment containing pip.
        :param raises: Expected exception to intercept. If provided, the raised exception
            will be returned instead of exit code (see pytest.raises and pytest.ExceptionInfo).
        :return: Command results (stdout, stderr, exit code or pytest.ExceptionInfo).
        """
        # build command using python -m pip (more reliable than finding pip executable)
        prefix_path = Path(prefix)
        python_exe = prefix_path / PYTHON_BINARY
        cmd = [str(python_exe), "-m", "pip"] + [str(arg) for arg in argv]

        # run command
        with pytest.raises(raises) if raises else nullcontext() as exception:
            try:
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    check=True,
                )
                code = result.returncode
                stdout = result.stdout
                stderr = result.stderr
            except subprocess.CalledProcessError as e:
                code = e.returncode
                stdout = e.stdout
                stderr = e.stderr
            except FileNotFoundError:
                # python executable not found
                raise RuntimeError(
                    f"Python not found in environment {prefix_path}: {python_exe}"
                )

        return stdout, stderr, exception if raises else code


@pytest.fixture(scope="session")
def pip_cli() -> Iterator[PipCLIFixture]:
    """A function scoped fixture returning PipCLIFixture instance.

    Use this for calling pip commands in specific conda environments during tests.
    Uses `python -m pip` for reliable cross-platform execution.

    Example:
        def test_pip_install(tmp_env, pip_cli):
            with tmp_env("python=3.10", "pip") as prefix:
                stdout, stderr, code = pip_cli("install", "requests", prefix=prefix)
                assert code == 0
    """
    yield PipCLIFixture()


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
        name = name or uuid.uuid4().hex[:8]
        suffix = suffix or ""
        return self.tmp_path / (prefix + name + suffix)


@pytest.fixture
def path_factory(tmp_path: Path) -> Iterator[PathFactoryFixture]:
    """A function scoped fixture returning PathFactoryFixture instance.

    Use this to generate any number of temporary paths for the test that are unique and
    do not exist yet.
    """
    yield PathFactoryFixture(tmp_path)


@dataclass
class TmpEnvFixture:
    path_factory: PathFactoryFixture | TempPathFactory
    conda_cli: CondaCLIFixture

    def get_path(self) -> Path:
        if isinstance(self.path_factory, PathFactoryFixture):
            # scope=function
            return self.path_factory()
        else:
            # scope=session
            return self.path_factory.mktemp("tmp_env-")

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
        prefix = Path(prefix or self.get_path())

        self.conda_cli("create", "--prefix", prefix, *packages, "--yes", "--quiet")
        yield prefix

        # no need to remove prefix since it is in a temporary directory


@pytest.fixture
def tmp_env(
    path_factory: PathFactoryFixture,
    conda_cli: CondaCLIFixture,
) -> Iterator[TmpEnvFixture]:
    """A function scoped fixture returning TmpEnvFixture instance.

    Use this when creating a conda environment that is local to the current test.
    """
    yield TmpEnvFixture(path_factory, conda_cli)


@pytest.fixture(scope="session")
def session_tmp_env(
    tmp_path_factory: TempPathFactory,
    session_conda_cli: CondaCLIFixture,
) -> Iterator[TmpEnvFixture]:
    """A session scoped fixture returning TmpEnvFixture instance.

    Use this when creating a conda environment that is shared across tests.
    """
    yield TmpEnvFixture(tmp_path_factory, session_conda_cli)


@dataclass
class TmpChannelFixture:
    path_factory: PathFactoryFixture
    conda_cli: CondaCLIFixture

    @contextmanager
    def __call__(self, *specs: str) -> Iterator[tuple[Path, str]]:
        # download packages
        self.conda_cli(
            "create",
            f"--prefix={self.path_factory()}",
            *specs,
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
        iter_specs = list(specs)
        seen: dict[str, set[str]] = {}
        while iter_specs:
            spec = iter_specs.pop(0)

            for package_record in pkgs_cache.query(spec):
                # track which packages have already been copied to the channel
                fname = package_record["fn"]
                if fname in seen:
                    seen[fname].add(spec)
                seen[fname] = {spec}

                # copy package to channel
                copyfile(pkgs_dir / fname, subdir / fname)

                # add package to repodata
                repodata["packages"][fname] = PackageRecord(
                    **{
                        field: value
                        for field, value in package_record.dump().items()
                        if field not in ("url", "channel", "schannel", "channel_name")
                    }
                )

                iter_specs.extend(package_record.depends)

        (subdir / "repodata.json").write_text(json.dumps(repodata))
        (noarch / "repodata.json").write_text(json.dumps({}))

        # ensure all packages were copied to the channel
        for spec in chain.from_iterable(seen.values()):
            assert any(PackageCacheData(pkgs_dir).query(spec))

        yield channel, path_to_url(str(channel))


@pytest.fixture
def tmp_channel(
    path_factory: PathFactoryFixture,
    conda_cli: CondaCLIFixture,
) -> Iterator[TmpChannelFixture]:
    """A function scoped fixture returning TmpChannelFixture instance."""
    yield TmpChannelFixture(path_factory, conda_cli)


@pytest.fixture(name="monkeypatch")
def context_aware_monkeypatch(monkeypatch: MonkeyPatch) -> MonkeyPatch:
    """A monkeypatch fixture that resets context after each test."""
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
def tmp_pkgs_dir(
    path_factory: PathFactoryFixture, mocker: MockerFixture
) -> Iterator[Path]:
    """A function scoped fixture returning a temporary package cache directory."""
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


@pytest.fixture
def tmp_envs_dir(
    path_factory: PathFactoryFixture, mocker: MockerFixture
) -> Iterator[Path]:
    """A function scoped fixture returning a temporary environment directory."""
    envs_dir = path_factory() / "envs"
    envs_dir.mkdir(parents=True)

    mocker.patch(
        "conda.base.context.Context.envs_dirs",
        new_callable=mocker.PropertyMock,
        return_value=(envs_dir_str := str(envs_dir),),
    )
    assert context.envs_dirs == (envs_dir_str,)

    yield envs_dir


@pytest.fixture(scope="session", autouse=True)
def PYTHONPATH():
    """
    We need to set this so Python loads the dev version of 'conda', usually taken
    from `conda/` in the root of the cloned repo. This root is usually the working
    directory when we run `pytest`.
    Otherwise, it will import the one installed in the base environment, which might
    have not been overwritten with `pip install -e . --no-deps`. This doesn't happen
    in other tests because they run with the equivalent of `python -m conda`. However,
    some tests directly run `conda (shell function) which calls `conda` (Python entry
    point). When a script is called this way, it bypasses the automatic "working directory
    is first on sys.path" behavior you find in `python -m` style calls. See
    https://docs.python.org/3/library/sys_path_init.html for details.
    """
    if "PYTHONPATH" in os.environ:
        yield
    else:
        with pytest.MonkeyPatch.context() as monkeypatch:
            monkeypatch.setenv("PYTHONPATH", CONDA_SOURCE_ROOT)
            yield


@pytest.fixture
def context_testdata() -> None:
    reset_context()
    context._set_raw_data(
        {
            "testdata": YamlRawParameter.make_raw_parameters(
                "testdata", yaml_round_trip_load(TEST_CONDARC)
            )
        }
    )
