# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""Tools for managing the packages installed within an environment."""

from __future__ import annotations

import os
import re
from logging import getLogger
from os.path import basename, lexists
from pathlib import Path
from typing import TYPE_CHECKING

from ..base.constants import (
    CONDA_ENV_VARS_UNSET_VAR,
    CONDA_PACKAGE_EXTENSIONS,
    PREFIX_FROZEN_FILE,
    PREFIX_MAGIC_FILE,
    PREFIX_NAME_DISALLOWED_CHARS,
    PREFIX_PINNED_FILE,
    PREFIX_STATE_FILE,
    RESERVED_ENV_NAMES,
    ROOT_ENV_NAME,
)
from ..base.context import context, locate_prefix_by_name
from ..common.compat import on_win
from ..common.constants import NULL
from ..common.io import time_recorder
from ..common.path import expand, paths_equal
from ..common.serialize import json
from ..common.url import mask_anaconda_token
from ..common.url import remove_auth as url_remove_auth
from ..deprecations import deprecated
from ..exceptions import (
    BasicClobberError,
    CondaDependencyError,
    CondaError,
    CondaValueError,
    CorruptedEnvironmentError,
    DirectoryNotACondaEnvironmentError,
    EnvironmentIsFrozenError,
    EnvironmentLocationNotFound,
    EnvironmentNameNotFound,
    EnvironmentNotWritableError,
    maybe_raise,
)
from ..gateways.disk.create import first_writable_envs_dir, write_as_json_to_file
from ..gateways.disk.delete import rm_rf
from ..gateways.disk.test import file_path_is_writable
from ..models.enums import PackageType
from ..models.match_spec import MatchSpec
from ..models.prefix_graph import PrefixGraph
from ..models.records import PackageRecord, PrefixRecord

if TYPE_CHECKING:
    from collections.abc import Iterable
    from typing import Any, TypeVar

    from ..auxlib import _Null
    from ..common.path import PathType

    T = TypeVar("T")

log = getLogger(__name__)


class PrefixDataType(type):
    """Basic caching of PrefixData instance objects."""

    @deprecated.argument(
        "25.9", "26.3", "pip_interop_enabled", rename="interoperability"
    )
    def __call__(
        cls,
        prefix_path: PathType,
        interoperability: bool | None = None,
    ) -> PrefixData:
        if isinstance(prefix_path, PrefixData):
            return prefix_path
        prefix_path = Path(prefix_path)
        interoperability = (
            interoperability
            if interoperability is not None
            else context.prefix_data_interoperability
        )
        cache_key = prefix_path, interoperability
        if cache_key in PrefixData._cache_:
            return PrefixData._cache_[cache_key]
        else:
            prefix_data_instance = super().__call__(prefix_path, interoperability)
            PrefixData._cache_[cache_key] = prefix_data_instance
            return prefix_data_instance


class PrefixData(metaclass=PrefixDataType):
    """
    The PrefixData class aims to be the representation of the state
    of a conda environment on disk. The directory where the environment
    lives is called prefix.

    This class supports different types of tasks:

    - Reading and querying `conda-meta/*.json` files as `PrefixRecord` objects
    - Reading and writing environment-specific configuration (env vars, state file,
      nonadmin markers, etc)
    - Existence checks and validations of name, path, and magic files / markers
    - Exposing non-conda packages installed in prefix as `PrefixRecord`, via the plugin system
    """

    _cache_: dict[tuple[Path, bool | None], PrefixData] = {}

    @deprecated.argument(
        "25.9", "26.3", "pip_interop_enabled", rename="interoperability"
    )
    def __init__(
        self,
        prefix_path: PathType,
        interoperability: bool | None = None,
    ):
        # pip_interop_enabled is a temporary parameter; DO NOT USE
        # TODO: when removing pip_interop_enabled, also remove from meta class
        self.prefix_path: Path = Path(prefix_path)
        self._magic_file: Path = self.prefix_path / PREFIX_MAGIC_FILE
        self._frozen_file: Path = self.prefix_path / PREFIX_FROZEN_FILE
        self.__prefix_records: dict[str, PrefixRecord] | None = None
        self.__is_writable: bool | None | _Null = NULL
        self.interoperability: bool = (
            interoperability
            if interoperability is not None
            else context.prefix_data_interoperability
        )

    @classmethod
    def from_name(cls, name: str, **kwargs) -> PrefixData:
        """
        Creates a PrefixData instance from an environment name.

        The name will be validated with `PrefixData.validate_name()` if it does not exist.

        :param name: The name of the environment. Must not contain path separators (/, \\).
        :raises CondaValueError: If `name` contains a path separator.
        """
        if "/" in name or "\\" in name:
            raise CondaValueError("Environment names cannot contain path separators")
        try:
            return cls(locate_prefix_by_name(name))
        except EnvironmentNameNotFound:
            cls(name).validate_name()
            return cls(Path(first_writable_envs_dir(), name), **kwargs)

    @classmethod
    def from_context(cls, validate: bool = False) -> PrefixData:
        """
        Creates a PrefixData instance from the path specified by `context.target_prefix`.

        The path and name will be validated with `PrefixData.validate_path()` and
        `PrefixData.validate_name()`, respectively, if `validate` is `True`.

        :param validate: Whether the path and name should be validated. Useful for environments
            about to be created.
        """
        inst = cls(context.target_prefix)
        if validate:
            inst.validate_path()
            inst.validate_name()
        return inst

    @property
    def name(self) -> str:
        """
        Returns the name of the environment, if available.

        If the environment doesn't live in one the configured `envs_dirs`, an empty
        string is returned. The construct `prefix_data.name or prefix_data.prefix_path` can
        be helpful in those cases.
        """
        if self == PrefixData(context.root_prefix):
            return ROOT_ENV_NAME
        for envs_dir in context.envs_dirs:
            if paths_equal(envs_dir, self.prefix_path.parent):
                return self.prefix_path.name
        return ""

    # region Checks

    def __eq__(self, other: Any) -> bool:
        if not isinstance(other, PrefixData):
            return False
        if self.prefix_path.exists():
            if other.prefix_path.exists():
                return self.prefix_path.samefile(other.prefix_path)
            return False  # only one prefix exists, cannot be the same
        elif other.prefix_path.exists():
            return False  # only one prefix exists, cannot be the same
        else:
            # neither prefix exists, raw comparison
            return self.prefix_path.resolve() == other.prefix_path.resolve()

    def exists(self) -> bool:
        """
        Check whether the PrefixData path exists and is a directory.
        """
        try:
            return self.prefix_path.is_dir()
        except OSError:
            return False

    def is_environment(self) -> bool:
        """
        Check whether the PrefixData path is a valida conda environment.

        This is assessed by checking if `conda-meta/history` marker file exists.
        """
        try:
            return self._magic_file.is_file()
        except OSError:
            return False

    def is_frozen(self) -> bool:
        """
        Check whether the environment is marked as frozen, as per CEP 22.

        This is assessed by checking if `conda-meta/frozen` marker file exists.
        """
        try:
            return self._frozen_file.is_file()
        except OSError:
            return False

    def is_base(self) -> bool:
        """
        Check whether the configured path refers to the `base` environment.
        """
        return paths_equal(str(self.prefix_path), context.root_prefix)

    @property
    def is_writable(self) -> bool | None | _Null:
        """
        Check whether the configured path is writable. This is assessed by checking
        whether `conda-meta/history` is writable. It if is, it is assumed that the rest
        of the directory tree is writable too.

        Note: The value is cached in the instance. Use `.assert_writable()` for a non-
        cached check.
        """
        if self.__is_writable == NULL:
            if not self.is_environment():
                is_writable = None
            else:
                is_writable = file_path_is_writable(self._magic_file)
            self.__is_writable = is_writable
        return self.__is_writable

    def assert_exists(self) -> None:
        """
        Check whether the environment path exists.

        :raises EnvironmentLocationNotFound: If the check returns False.
        """
        if not self.exists():
            raise EnvironmentLocationNotFound(self.prefix_path)

    def assert_environment(self) -> None:
        """
        Check whether the environment path exists and is a valid conda environment.

        :raises DirectoryNotACondaEnvironmentError: If the check returns False.
        """
        self.assert_exists()
        if not self.is_environment():
            raise DirectoryNotACondaEnvironmentError(self.prefix_path)

    def assert_writable(self) -> None:
        """
        Check whether the environment path is a valid conda environment and is writable.

        :raises EnvironmentNotWritableError: If the check returns False.
        """
        self.assert_environment()
        if not file_path_is_writable(self._magic_file):
            raise EnvironmentNotWritableError(self.prefix_path)

    def assert_not_frozen(self) -> None:
        """
        Check whether the environment path is a valid conda environment and is not marked
        as frozen (as per CEP 22).

        :raises EnvironmentIsFrozenError: If the environment is marked as frozen.
        """
        self.assert_environment()
        if not self.is_frozen():
            return
        message = ""
        contents = self._frozen_file.read_text()
        if contents:
            message = json.loads(contents).get("message", "")
        raise EnvironmentIsFrozenError(self.prefix_path, message)

    def validate_path(self, expand_path: bool = False) -> None:
        """
        Validate the path of the environment.

        It runs the following checks:

        - Make sure the path does not contain `:` or `;` (OS-dependent).
        - Disallow immediately nested environments (e.g. `$CONDA_ROOT` and `$CONDA_ROOT/my-env`).
        - Warn if there are spaces in the path.

        :param expand_path: Whether to process `~` and environment variables in the string.
            The expanded value will replace `.prefix_path`.
        :raises CondaValueError: If the environment contains `:`, `;`, or is nested.
        """
        prefix_str = str(self.prefix_path)
        if expand_path:
            prefix_str = expand(prefix_str)
            self.prefix_path = Path(prefix_str)

        if os.pathsep in prefix_str:
            raise CondaValueError(
                f"Environment paths cannot contain '{os.pathsep}'. Prefix: '{prefix_str}'"
            )

        if " " in prefix_str:
            log.warning(
                "Environment paths should not contain spaces. Prefix: '%s'",
                prefix_str,
            )
        parent = self.__class__(self.prefix_path.parent)
        if parent.is_environment():
            raise CondaValueError(
                "Environment paths cannot be immediately nested under another conda environment."
            )

    def validate_name(self, allow_base: bool = False) -> None:
        """
        Validate the name of the environment.

        :param allow_base: Whether to allow `base` as a valid name.
        :raises CondaValueError: If the name is protected, or if it contains disallowed characters
            (`/`, ` `, `:`, `#`).
        """
        if not allow_base and self.name in RESERVED_ENV_NAMES:
            raise CondaValueError(f"'{self.name}' is a reserved environment name")

        if PREFIX_NAME_DISALLOWED_CHARS.intersection(self.prefix_path.name):
            raise CondaValueError(
                "Environment names cannot contain any of these characters: "
                f"{PREFIX_NAME_DISALLOWED_CHARS}"
            )

    # endregion
    # region Records

    @time_recorder(module_name=__name__)
    def load(self) -> None:
        self.__prefix_records = {}
        _conda_meta_dir = self.prefix_path / "conda-meta"
        if lexists(_conda_meta_dir):
            conda_meta_json_paths = (
                p
                for p in (entry.path for entry in os.scandir(_conda_meta_dir))
                if p[-5:] == ".json"
            )
            for meta_file in conda_meta_json_paths:
                self._load_single_record(meta_file)
        if self.interoperability:
            for loader in context.plugin_manager.get_prefix_data_loaders():
                loader(self.prefix_path, self.__prefix_records)

    def reload(self) -> PrefixData:
        self.load()
        return self

    @property
    @deprecated("25.9", "26.3", addendum="Use PrefixData.interoperability.")
    def _pip_interop_enabled(self):
        return self.interoperability

    def _get_json_fn(self, prefix_record: PrefixRecord) -> str:
        fn = prefix_record.fn
        known_ext = False
        # .dist-info is for things installed by pip
        for ext in CONDA_PACKAGE_EXTENSIONS + (".dist-info",):
            if fn.endswith(ext):
                fn = fn[: -len(ext)]
                known_ext = True
        if not known_ext:
            raise ValueError(
                f"Attempted to make prefix record for unknown package type: {fn}"
            )
        return fn + ".json"

    def insert(self, prefix_record: PrefixRecord, remove_auth: bool = True) -> None:
        if prefix_record.name in self._prefix_records:
            raise CondaError(
                f"Prefix record '{prefix_record.name}' already exists. "
                f"Try `conda clean --all` to fix."
            )

        prefix_record_json_path = (
            self.prefix_path / "conda-meta" / self._get_json_fn(prefix_record)
        )
        if lexists(prefix_record_json_path):
            maybe_raise(
                BasicClobberError(
                    source_path=None,
                    target_path=prefix_record_json_path,
                    context=context,
                ),
                context,
            )
            rm_rf(prefix_record_json_path)
        if remove_auth:
            prefix_record_json = prefix_record.dump()
            prefix_record_json["url"] = url_remove_auth(
                mask_anaconda_token(prefix_record.url)
            )
        else:
            prefix_record_json = prefix_record
        write_as_json_to_file(prefix_record_json_path, prefix_record_json)

        self._prefix_records[prefix_record.name] = prefix_record

    def remove(self, package_name: str) -> None:
        assert package_name in self._prefix_records

        prefix_record = self._prefix_records[package_name]

        prefix_record_json_path = (
            self.prefix_path / "conda-meta" / self._get_json_fn(prefix_record)
        )
        if self.is_writable:
            rm_rf(prefix_record_json_path)

        del self._prefix_records[package_name]

    def get(self, package_name: str, default: T = NULL) -> PackageRecord | T:
        try:
            return self._prefix_records[package_name]
        except KeyError:
            if default is not NULL:
                return default
            else:
                raise

    def iter_records(self) -> Iterable[PrefixRecord]:
        return iter(self._prefix_records.values())

    def iter_records_sorted(self) -> Iterable[PrefixRecord]:
        prefix_graph = PrefixGraph(self.iter_records())
        return iter(prefix_graph.graph)

    def all_subdir_urls(self) -> set[str]:
        subdir_urls = set()
        for prefix_record in self.iter_records():
            subdir_url = prefix_record.channel.subdir_url
            if subdir_url and subdir_url not in subdir_urls:
                log.debug("adding subdir url %s for %s", subdir_url, prefix_record)
                subdir_urls.add(subdir_url)
        return subdir_urls

    def query(
        self, package_ref_or_match_spec: PackageRecord | MatchSpec | str
    ) -> Iterable[PrefixRecord]:
        # returns a generator
        param = package_ref_or_match_spec
        if isinstance(param, str):
            param = MatchSpec(param)
        if isinstance(param, MatchSpec):
            return (
                prefix_rec
                for prefix_rec in self.iter_records()
                if param.match(prefix_rec)
            )
        else:
            assert isinstance(param, PackageRecord)
            return (
                prefix_rec for prefix_rec in self.iter_records() if prefix_rec == param
            )

    def get_conda_packages(self) -> list[PrefixRecord]:
        """Get conda packages sorted alphabetically by name.

        :return: Sorted conda package records
        """
        conda_types = {None, PackageType.NOARCH_GENERIC, PackageType.NOARCH_PYTHON}
        conda_packages = [
            record
            for record in self.iter_records()
            if record.package_type in conda_types
        ]
        return sorted(conda_packages, key=lambda x: x.name)

    def get_python_packages(self) -> list[PrefixRecord]:
        """Get Python packages (installed via pip) sorted alphabetically by name.

        :return: Sorted Python package records
        """
        python_types = {
            PackageType.VIRTUAL_PYTHON_WHEEL,
            PackageType.VIRTUAL_PYTHON_EGG_MANAGEABLE,
            PackageType.VIRTUAL_PYTHON_EGG_UNMANAGEABLE,
        }
        python_packages = [
            record
            for record in self.iter_records()
            if record.package_type in python_types
        ]
        return sorted(python_packages, key=lambda x: x.name)

    @property
    def _prefix_records(self) -> dict[str, PrefixRecord] | None:
        return self.__prefix_records or self.load() or self.__prefix_records

    def _load_single_record(self, prefix_record_json_path: PathType) -> None:
        log.debug("loading prefix record %s", prefix_record_json_path)
        with open(prefix_record_json_path) as fh:
            try:
                json_data = json.load(fh)
            except (UnicodeDecodeError, json.JSONDecodeError):
                # UnicodeDecodeError: catch horribly corrupt files
                # json.JSONDecodeError: catch bad json format files
                raise CorruptedEnvironmentError(
                    self.prefix_path, prefix_record_json_path
                )

            # TODO: consider, at least in memory, storing prefix_record_json_path as part
            #       of PrefixRecord
            prefix_record = PrefixRecord(**json_data)

            # check that prefix record json filename conforms to name-version-build
            # apparently implemented as part of #2638 to resolve #2599
            try:
                n, v, b = basename(prefix_record_json_path)[:-5].rsplit("-", 2)
                if (n, v, b) != (
                    prefix_record.name,
                    prefix_record.version,
                    prefix_record.build,
                ):
                    raise ValueError()
            except ValueError:
                log.warning(
                    "Ignoring malformed prefix record at: %s", prefix_record_json_path
                )
                # TODO: consider just deleting here this record file in the future
                return

            self.__prefix_records[prefix_record.name] = prefix_record

    # endregion
    # region Python records

    @property
    @deprecated("25.9", "26.3", addendum="Use PrefixData.get('python').")
    def _python_pkg_record(self) -> PrefixRecord | None:
        """Return the prefix record for the package python."""
        return next(
            (
                prefix_record
                for prefix_record in self.__prefix_records.values()
                if prefix_record.name == "python"
            ),
            None,
        )

    @deprecated(
        "25.9",
        "26.3",
        addendum="Use 'conda.plugins.prefix_data_loaders.pypi.load_site_packages' instead.",
    )
    def _load_site_packages(self) -> dict[str, PrefixRecord]:
        from ..plugins.prefix_data_loaders.pypi import load_site_packages

        return load_site_packages(self.prefix_path, self.__prefix_records)

    # endregion
    # region State and environment variables

    def _get_environment_state_file(self) -> dict[str, dict[str, str]]:
        env_vars_file = self.prefix_path / PREFIX_STATE_FILE
        if lexists(env_vars_file):
            with open(env_vars_file) as f:
                prefix_state = json.loads(f.read())
        else:
            prefix_state = {}
        return prefix_state

    def _write_environment_state_file(self, state: dict[str, dict[str, str]]) -> None:
        env_vars_file = self.prefix_path / PREFIX_STATE_FILE
        env_vars_file.write_text(json.dumps(state, ensure_ascii=False))

    def get_environment_env_vars(self) -> dict[str, str] | dict[bytes, bytes]:
        prefix_state = self._get_environment_state_file()
        env_vars_all = dict(prefix_state.get("env_vars", {}))
        env_vars = {
            k: v for k, v in env_vars_all.items() if v != CONDA_ENV_VARS_UNSET_VAR
        }
        return env_vars

    def set_environment_env_vars(
        self, env_vars: dict[str, str]
    ) -> dict[str, str] | None:
        env_state_file = self._get_environment_state_file()
        current_env_vars = env_state_file.get("env_vars")
        if current_env_vars:
            current_env_vars.update(env_vars)
        else:
            env_state_file["env_vars"] = env_vars
        self._write_environment_state_file(env_state_file)
        return env_state_file.get("env_vars")

    def unset_environment_env_vars(
        self, env_vars: dict[str, str]
    ) -> dict[str, str] | None:
        env_state_file = self._get_environment_state_file()
        current_env_vars = env_state_file.get("env_vars")
        if current_env_vars:
            for env_var in env_vars:
                if env_var in current_env_vars.keys():
                    current_env_vars[env_var] = CONDA_ENV_VARS_UNSET_VAR
            self._write_environment_state_file(env_state_file)
        return env_state_file.get("env_vars")

    def set_nonadmin(self) -> None:
        """Creates $PREFIX/.nonadmin if sys.prefix/.nonadmin exists (on Windows)."""
        if on_win and Path(context.root_prefix, ".nonadmin").is_file():
            self.prefix_path.mkdir(parents=True, exist_ok=True)
            (self.prefix_path / ".nonadmin").touch()

    def get_pinned_specs(self) -> tuple[MatchSpec]:
        """Find pinned specs from file and return a tuple of MatchSpec."""
        pin_file = self.prefix_path / PREFIX_PINNED_FILE
        if pin_file.exists():
            with pin_file.open() as f:
                from_file = (
                    i
                    for i in f.read().strip().splitlines()
                    if i and not i.strip().startswith("#")
                )
        else:
            from_file = ()

        return tuple(MatchSpec(spec, optional=True) for spec in from_file)

    # endregion


def get_conda_anchor_files_and_records(
    site_packages_short_path: PathType, python_records: Iterable[PrefixRecord]
) -> dict[PathType, PrefixRecord]:
    """Return the anchor files for the conda records of python packages."""
    anchor_file_endings = (".egg-info/PKG-INFO", ".dist-info/RECORD", ".egg-info")
    conda_python_packages = {}

    matcher = re.compile(
        r"^{}/[^/]+(?:{})$".format(
            re.escape(site_packages_short_path),
            r"|".join(re.escape(fn) for fn in anchor_file_endings),
        )
    ).match

    # We could fix this earlier in the PrefixRecord instantiation, but then
    # we would pay for this conversion every time we load any record.
    # However we only need this fix for conda list, which is the only one
    # that uses PrefixData with pip_interop_enabled=True. This function is
    # only called in that code path.
    # See https://github.com/conda/conda/pull/14523 for more context.
    for prefix_record in python_records:
        anchor_paths = []
        for fpath in prefix_record.files:
            if on_win:
                fpath = fpath.replace("\\", "/")
            if matcher(fpath):
                anchor_paths.append(fpath)
        if len(anchor_paths) > 1:
            anchor_path = sorted(anchor_paths, key=len)[0]
            log.info(
                "Package %s has multiple python anchor files.\n  Using %s",
                prefix_record.record_id(),
                anchor_path,
            )
            conda_python_packages[anchor_path] = prefix_record
        elif anchor_paths:
            conda_python_packages[anchor_paths[0]] = prefix_record

    return conda_python_packages


@deprecated("25.9", "26.3", addendum="Use `PrefixData.get('python', None)` instead.")
def python_record_for_prefix(prefix: os.PathLike) -> PrefixRecord | None:
    """
    For the given conda prefix, return the PrefixRecord of the Python installed
    in that prefix.
    """
    python_record_iterator = (
        record
        for record in PrefixData(prefix).iter_records()
        if record.name == "python"
    )
    record = next(python_record_iterator, None)
    if record is not None:
        next_record = next(python_record_iterator, None)
        if next_record is not None:
            raise CondaDependencyError(
                f"multiple python records found in prefix {prefix}"
            )
    return record


@deprecated("25.9", "26.3", addendum="Use `PrefixData.get('python').version` instead.")
def get_python_version_for_prefix(prefix: os.PathLike) -> str | None:
    """
    For the given conda prefix, return the version of the Python installation
    in that prefix.
    """
    # returns a string e.g. "2.7", "3.4", "3.5" or None
    record = PrefixData(prefix).get("python", None)
    if record is not None:
        if record.version[3].isdigit():
            return record.version[:4]
        else:
            return record.version[:3]
    return None


def delete_prefix_from_linked_data(path: str | os.PathLike | Path) -> bool:
    """Here, path may be a complete prefix or a dist inside a prefix"""
    path = Path(path)
    for prefix, interoperability in sorted(
        PrefixData._cache_, reverse=True, key=lambda key: key[0]
    ):
        try:
            path.relative_to(prefix)
            del PrefixData._cache_[(prefix, interoperability)]
            return True
        except ValueError:
            # ValueError: path is not relative to prefix
            continue
    return False
