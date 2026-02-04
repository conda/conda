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
from ..base.constants import PACKAGE_CACHE_MAGIC_FILE, PREFIX_MAGIC_FILE
from ..base.context import context, reset_context
from ..cli.main import main_subshell
from ..common.configuration import YamlRawParameter
from ..common.serialize import json, yaml
from ..common.url import path_to_url
from ..core.package_cache_data import PackageCacheData
from ..core.subdir_data import SubdirData
from ..exceptions import CondaExitZero, InvalidMatchSpec
from ..gateways.disk.create import TemporaryDirectory
from ..models.match_spec import MatchSpec
from ..models.records import PackageRecord
from .integration import PYTHON_BINARY

if TYPE_CHECKING:
    import http.server
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


@dataclass
class TemplateEnvManager:
    """Manages a single template environment for fast cloning.

    Creates one template environment with Python + pip at session start.
    Tests can clone from this template if all their required packages
    are present in the template (checked by package name).

    This is simpler than version-specific templates and benefits tests
    that use generic "python" or "python" + "pip" specs.
    """

    template_path: Path | None = None
    _installed_packages: set[str] | None = None

    @property
    def installed_packages(self) -> set[str]:
        """Get set of package names installed in the template."""
        if self._installed_packages is None:
            self._installed_packages = set()
            if self.template_path and self.template_path.exists():
                from ..core.prefix_data import PrefixData

                try:
                    self._installed_packages = {
                        rec.name
                        for rec in PrefixData(self.template_path).iter_records()
                    }
                except Exception:
                    pass
        return self._installed_packages

    def can_satisfy(self, specs: tuple[str, ...]) -> bool:
        """Check if template has all packages required by specs.

        Only matches specs WITHOUT version constraints:
        - "python" matches if template has python
        - "pip" matches if template has pip
        - "python=3.10" does NOT match (has version constraint)
        - "numpy>=1.0" does NOT match (has version constraint)

        This conservative approach ensures we only clone when the template
        definitely has what the test needs.

        Args:
            specs: Package specs requested by the test

        Returns:
            True if template has all required packages and no version constraints
        """
        if not self.template_path or not self.template_path.exists():
            return False

        if not specs:
            return False

        # Extract package names from specs
        # Skip flags (start with -)
        required_names: set[str] = set()
        has_flags = False

        for spec in specs:
            spec_str = str(spec)
            if spec_str.startswith("-"):
                has_flags = True
                continue
            try:
                match_spec = MatchSpec(spec_str)
                # If spec has ANY version constraint, don't clone
                # Version might not match what's in template
                if match_spec.version:
                    log.debug(
                        "Spec %r has version constraint, skipping clone", spec_str
                    )
                    return False
                required_names.add(match_spec.name)
            except InvalidMatchSpec:
                # If we can't parse the spec, be conservative
                return False

        # Don't clone if flags are present (might affect environment)
        if has_flags:
            return False

        # Check if template has all required packages
        missing = required_names - self.installed_packages
        if missing:
            log.debug("Template missing packages: %s", missing)
            return False

        return True


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
def temp_package_cache(tmp_path_factory, monkeypatch: MonkeyPatch) -> Iterator[Path]:
    """
    Used to isolate package or index cache from other tests.
    """
    pkgs_dir = tmp_path_factory.mktemp("pkgs")
    monkeypatch.setenv("CONDA_PKGS_DIRS", str(pkgs_dir))
    reset_context()
    yield pkgs_dir


@pytest.fixture(
    # allow CI to set the solver backends via the CONDA_TEST_SOLVERS env var
    params=os.environ.get("CONDA_TEST_SOLVERS", "libmamba,classic").split(",")
)
def parametrized_solver_fixture(
    request: FixtureRequest,
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
    yield from _solver_helper(request, request.param)


@pytest.fixture
def solver_classic(
    request: FixtureRequest,
) -> Iterable[Literal["classic"]]:
    yield from _solver_helper(request, "classic")


@pytest.fixture
def solver_libmamba(
    request: FixtureRequest,
) -> Iterable[Literal["libmamba"]]:
    yield from _solver_helper(request, "libmamba")


Solver = TypeVar("Solver", Literal["libmamba"], Literal["classic"])


def _solver_helper(
    request: FixtureRequest,
    solver: Solver,
) -> Iterable[Solver]:
    # clear cached solver backends before & after each test
    context.plugin_manager.get_cached_solver_backend.cache_clear()
    request.addfinalizer(context.plugin_manager.get_cached_solver_backend.cache_clear)

    mp = request.getfixturevalue("monkeypatch")

    mp.setenv("CONDA_SOLVER", solver)
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
        *,
        prefix: str | None = None,
        infix: str | None = None,
        suffix: str | None = None,
    ) -> Path:
        """Unique, non-existent path factory.

        Extends pytest's `tmp_path` fixture with a new unique, non-existent path for usage in cases
        where we need a temporary path that doesn't exist yet.

        Default behavior (no arguments):
           ``path_factory()`` → ``tmp_path/ab12cd34ef56`` (12-char UUID)

        Two modes of operation (mutually exclusive):

        1. Name mode: Pass a complete path name.
           ``path_factory("myfile.txt")`` → ``tmp_path/myfile.txt``

        2. Parts mode: Pass prefix/infix/suffix; unspecified parts get UUID defaults.
           ``path_factory(infix="!")`` → ``tmp_path/ab12!ef56``
           ``path_factory(suffix=".yml")`` → ``tmp_path/ab12cd34.yml``

        :param name: Complete path name (mutually exclusive with prefix/infix/suffix)
        :param prefix: Prefix for generated name (mutually exclusive with name param)
        :param infix: Infix for generated name (mutually exclusive with name param)
        :param suffix: Suffix for generated name (mutually exclusive with name param)
        :return: A new unique path
        """
        if name and (prefix or infix or suffix):
            raise ValueError(
                "name and (prefix or infix or suffix) are mutually exclusive"
            )
        elif name:
            return self.tmp_path / name
        else:
            random = uuid.uuid4().hex
            prefix = prefix or random[:4]
            infix = infix or random[4:8]
            suffix = suffix or random[8:12]
            return self.tmp_path / (prefix + infix + suffix)


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
    template_manager: TemplateEnvManager | None = None

    def get_path(
        self,
        name: str | None = None,
        prefix: str | None = None,
        infix: str | None = None,
        suffix: str | None = None,
    ) -> Path:
        if isinstance(self.path_factory, PathFactoryFixture):
            # scope=function
            return self.path_factory(
                name=name,
                prefix=prefix,
                infix=infix,
                suffix=suffix,
            )
        else:
            # scope=session
            return self.path_factory.mktemp(
                name or ((prefix or "tmp_env-") + (infix or "") + (suffix or ""))
            )

    @contextmanager
    def __call__(
        self,
        *args: str,
        prefix: str | os.PathLike | None = None,
        name: str | None = None,
        path_prefix: str | None = None,
        path_infix: str | None = None,
        path_suffix: str | None = None,
        shallow: bool | None = None,
    ) -> Iterator[Path]:
        """Generate a conda environment with the provided packages.

        Path customization (mutually exclusive options):

        1. Auto-generated path (default): Unique path in tmp_path.
           ``tmp_env()`` → ``tmp_path/ab12cd34ef56`` (12-char UUID)

        2. Custom prefix: Specify exact location.
           ``tmp_env(prefix="/path/to/env")`` → ``/path/to/env``

        3. Name mode: Specify env name directly.
           ``tmp_env(name="my-test-env")`` → ``tmp_path/my-test-env``

        4. Parts mode: Customize path name generation (useful for special char testing).
           ``tmp_env(path_infix="!")`` → ``tmp_path/ab12!ef56``

        :param args: Arguments to pass to conda create (e.g., packages, flags)
        :param prefix: Exact prefix path (mutually exclusive with name/path_* params)
        :param name: Env name (mutually exclusive with prefix/path_* params)
        :param path_prefix: Prefix for path name (mutually exclusive with prefix/name params)
        :param path_infix: Infix for path name (mutually exclusive with prefix/name params)
        :param path_suffix: Suffix for path name (mutually exclusive with prefix/name params)
        :param shallow: If True, create env on disk only without conda create
        :return: The conda environment's prefix
        """
        if shallow and args:
            raise ValueError("shallow=True cannot be used with any arguments")

        if prefix and (name or path_prefix or path_infix or path_suffix):
            raise ValueError(
                "prefix and (name or path_prefix or path_infix or path_suffix) are mutually exclusive"
            )

        prefix = Path(
            prefix
            or self.get_path(
                name,
                path_prefix,
                path_infix,
                path_suffix,
            )
        )

        if shallow or (shallow is None and not args):
            # no arguments, just create an empty environment
            path = prefix / PREFIX_MAGIC_FILE
            path.parent.mkdir(parents=True, exist_ok=True)
            path.touch()
        else:
            # Try to clone from template if it has all required packages
            # This is much faster than running conda create (~2s vs ~10s+)
            cloned = False

            if self.template_manager and self.template_manager.can_satisfy(args):
                # Use conda's native --clone functionality
                # This properly handles prefix replacement in scripts and metadata
                _, stderr, exit_code = self.conda_cli(
                    "create",
                    "--clone",
                    str(self.template_manager.template_path),
                    f"--prefix={prefix}",
                    "--yes",
                    "--quiet",
                )
                cloned = exit_code == 0
                if cloned:
                    log.debug(
                        "Cloned template env %s -> %s",
                        self.template_manager.template_path,
                        prefix,
                    )
                else:
                    log.debug(
                        "Clone failed (exit %d): %s, falling back to create",
                        exit_code,
                        stderr,
                    )

            if not cloned:
                # No template available or cloning failed - create from scratch
                self.conda_cli(
                    "create",
                    f"--prefix={prefix}",
                    *args,
                    "--yes",
                    "--quiet",
                )

        yield prefix

        # no need to remove prefix since it is in a temporary directory


@pytest.fixture(scope="session")
def template_env_manager(
    tmp_path_factory: TempPathFactory,
    session_conda_cli: CondaCLIFixture,
) -> Iterator[TemplateEnvManager | None]:
    """Create a session-scoped template environment for fast cloning.

    Creates ONE template environment with Python + pip at session start.
    Tests can clone from this template if all their required packages
    are present (checked by package name, not version).

    The cloning optimization uses `conda create --clone` which properly handles
    prefix replacement in scripts and metadata files (~2s vs ~10s for conda create).

    Benefits tests that request:
    - "python" (generic)
    - "python", "pip"
    - Any subset of packages in the template

    Yields:
        TemplateEnvManager instance, or None if template creation failed.
    """
    template_path = tmp_path_factory.mktemp("template_env")

    try:
        # Create template with Python + pip (common test requirements)
        _, stderr, exit_code = session_conda_cli(
            "create",
            f"--prefix={template_path}",
            "python",
            "pip",
            "--yes",
            "--quiet",
        )
        if exit_code != 0:
            log.warning("Failed to create template environment: %s", stderr)
            yield None
            return

        log.info("Created template environment at %s", template_path)
        yield TemplateEnvManager(template_path=template_path)

    except Exception as e:
        # Don't fail tests if template creation fails - just disable cloning
        log.warning("Failed to create template environment: %s", e)
        yield None


@pytest.fixture
def tmp_env(
    path_factory: PathFactoryFixture,
    conda_cli: CondaCLIFixture,
    template_env_manager: TemplateEnvManager | None,
) -> Iterator[TmpEnvFixture]:
    """A function scoped fixture returning TmpEnvFixture instance.

    Use this when creating a conda environment that is local to the current test.

    This fixture automatically uses environment cloning from a session-scoped
    template when all required packages are available in the template.
    Cloning is much faster than `conda create` (~2s vs ~10s+).

    Cloning is used when the test requests packages that are all present
    in the template (e.g., "python", "pip"). Otherwise, falls back to
    regular `conda create`.
    """
    yield TmpEnvFixture(path_factory, conda_cli, template_env_manager)


@pytest.fixture
def empty_env(tmp_env: TmpEnvFixture) -> Path:
    """A function scoped fixture returning an empty environment.

    Use this when creating a conda environment that is empty.
    """
    with tmp_env(shallow=True) as prefix:
        return prefix


@pytest.fixture(scope="session")
def session_tmp_env(
    tmp_path_factory: TempPathFactory,
    session_conda_cli: CondaCLIFixture,
    template_env_manager: TemplateEnvManager | None,
) -> Iterator[TmpEnvFixture]:
    """A session scoped fixture returning TmpEnvFixture instance.

    Use this when creating a conda environment that is shared across tests.

    This fixture automatically uses environment cloning from a session-scoped
    template when all required packages are available. Cloning is much faster
    than `conda create` (~2s vs ~10s+).
    """
    yield TmpEnvFixture(tmp_path_factory, session_conda_cli, template_env_manager)


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
                "testdata", yaml.loads(TEST_CONDARC)
            )
        }
    )


# HTTP Test Server Fixtures


@dataclass
class HttpTestServerFixture:
    """Fixture providing HTTP test server for serving local files."""

    server: http.server.ThreadingHTTPServer
    host: str
    port: int
    url: str
    directory: Path

    def __post_init__(self):
        """Log server startup for debugging."""
        log.debug(f"HTTP test server started: {self.url}")

    def get_url(self, path: str = "") -> str:
        """
        Get full URL for a given path on the server.

        :param path: Relative path on the server (e.g., "subdir/package.tar.bz2")
        :return: Full URL
        """
        path = path.lstrip("/")
        return f"{self.url}/{path}" if path else self.url


@pytest.fixture
def http_test_server(
    request: FixtureRequest,
    path_factory: PathFactoryFixture,
) -> Iterator[HttpTestServerFixture]:
    """
    Function-scoped HTTP test server for serving local files.

    This fixture starts an HTTP server on a random port and serves files
    from a directory. The server supports both IPv4 and IPv6.

    Usage without parametrize (dynamic content):
        def test_dynamic(http_test_server):
            # Server uses temporary directory automatically
            (http_test_server.directory / "file.txt").write_text("content")
            url = http_test_server.get_url("file.txt")
            response = requests.get(url)
            assert response.status_code == 200

    Usage with parametrize (pre-existing directory):
        @pytest.mark.parametrize("http_test_server", ["tests/data/mock-channel"], indirect=True)
        def test_existing(http_test_server):
            url = http_test_server.get_url("file.txt")
            response = requests.get(url)
            assert response.status_code == 200

    Use ``None`` in parametrize to mix pre-existing directories with dynamic content:
        @pytest.mark.parametrize("http_test_server", ["tests/data", None], indirect=True)

    :param request: pytest fixture request object
    :param path_factory: path_factory fixture for creating unique temp directories
    :return: HttpTestServerFixture with server, host, port, url, and directory attributes
    :raises ValueError: If parametrized directory is invalid
    """
    from . import http_test_server as http_server_module

    if directory := getattr(request, "param", None):
        # Parameter was provided via @pytest.mark.parametrize
        # Validate the provided directory
        directory_path = Path(directory)
        if not directory_path.exists():
            raise ValueError(f"Directory does not exist: {directory}")
        if not directory_path.is_dir():
            raise ValueError(f"Path is not a directory: {directory}")
        directory = str(directory_path.resolve())
    else:
        # No parameter provided or explicit None - use path_factory for unique directory
        server_dir = path_factory(name="http_test_server")
        server_dir.mkdir()
        directory = str(server_dir)

    server = http_server_module.run_test_server(directory)
    host, port = server.socket.getsockname()[:2]
    url_host = f"[{host}]" if ":" in host else host
    url = f"http://{url_host}:{port}"

    fixture = HttpTestServerFixture(
        server=server,
        host=host,
        port=port,
        url=url,
        directory=Path(directory),
    )

    yield fixture

    # Cleanup: shutdown server
    server.shutdown()
