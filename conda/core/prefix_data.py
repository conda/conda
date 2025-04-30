# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""Tools for managing the packages installed within an environment."""

from __future__ import annotations

import json
import os
import re
from logging import getLogger
from os.path import basename, lexists
from pathlib import Path
from typing import TYPE_CHECKING

from ..auxlib.exceptions import ValidationError
from ..base.constants import (
    CONDA_ENV_VARS_UNSET_VAR,
    CONDA_PACKAGE_EXTENSIONS,
    PREFIX_MAGIC_FILE,
    PREFIX_NAME_DISALLOWED_CHARS,
    PREFIX_STATE_FILE,
    ROOT_ENV_NAME,
)
from ..base.context import context, locate_prefix_by_name
from ..common.compat import on_win
from ..common.constants import NULL
from ..common.io import time_recorder
from ..common.path import (
    expand,
    get_python_site_packages_short_path,
    paths_equal,
    win_path_ok,
)
from ..common.pkg_formats.python import get_site_packages_anchor_files
from ..common.serialize import json_load
from ..common.url import mask_anaconda_token
from ..common.url import remove_auth as url_remove_auth
from ..exceptions import (
    BasicClobberError,
    CondaDependencyError,
    CondaValueError,
    CorruptedEnvironmentError,
    DirectoryNotACondaEnvironmentError,
    EnvironmentLocationNotFound,
    EnvironmentNameNotFound,
    EnvironmentNotWritableError,
    maybe_raise,
)
from ..gateways.disk.create import first_writable_envs_dir, write_as_json_to_file
from ..gateways.disk.delete import rm_rf
from ..gateways.disk.read import read_python_record
from ..gateways.disk.test import file_path_is_writable
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

    def __call__(
        cls,
        prefix_path: str | os.PathLike | Path,
        pip_interop_enabled: bool | None = None,
    ) -> PrefixData:
        if isinstance(prefix_path, PrefixData):
            return prefix_path
        prefix_path = Path(prefix_path)
        cache_key = prefix_path, pip_interop_enabled
        if cache_key in PrefixData._cache_:
            return PrefixData._cache_[cache_key]
        else:
            prefix_data_instance = super().__call__(prefix_path, pip_interop_enabled)
            PrefixData._cache_[cache_key] = prefix_data_instance
            return prefix_data_instance


class PrefixData(metaclass=PrefixDataType):
    """
    The PrefixData class aims to be the representation of the state
    of a conda environment on disk. The directory where the environment
    lives is called prefix.

    This class supports different types of tasks:

    - Reading and querying `conda-meta/*.json` files as `PackageRecord` objects
    - Reading PyPI-only packages, installed next to conda packages
    - Reading and writing environment-specific configuration (env vars, state file,
      nonadmin markers, etc)
    - Existence checks and validations of name, path, and magic files / markers
    """

    _cache_: dict[tuple[Path, bool | None], PrefixData] = {}

    def __init__(
        self,
        prefix_path: str | os.PathLike[str] | Path,
        pip_interop_enabled: bool | None = None,
    ):
        # pip_interop_enabled is a temporary parameter; DO NOT USE
        # TODO: when removing pip_interop_enabled, also remove from meta class
        self.prefix_path: Path = Path(prefix_path)
        self._magic_file: Path = self.prefix_path / PREFIX_MAGIC_FILE
        self.__prefix_records: dict[str, PrefixRecord] | None = None
        self.__is_writable: bool | None | _Null = NULL
        self._pip_interop_enabled: bool = (
            pip_interop_enabled
            if pip_interop_enabled is not None
            else context.pip_interop_enabled
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
        if not allow_base and self.name in (ROOT_ENV_NAME, "root"):
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
        if self._pip_interop_enabled:
            self._load_site_packages()

    def reload(self) -> PrefixData:
        self.load()
        return self

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
        assert prefix_record.name not in self._prefix_records, (
            f"Prefix record insertion error: a record with name {prefix_record.name} already exists "
            "in the prefix. This is a bug in conda. Please report it at "
            "https://github.com/conda/conda/issues"
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

    @property
    def _prefix_records(self) -> dict[str, PrefixRecord] | None:
        return self.__prefix_records or self.load() or self.__prefix_records

    def _load_single_record(self, prefix_record_json_path: PathType) -> None:
        log.debug("loading prefix record %s", prefix_record_json_path)
        with open(prefix_record_json_path) as fh:
            try:
                json_data = json_load(fh.read())
            except (UnicodeDecodeError, json.JSONDecodeError):
                # UnicodeDecodeError: catch horribly corrupt files
                # JSONDecodeError: catch bad json format files
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

    def _load_site_packages(self) -> dict[str, PrefixRecord]:
        """
        Load non-conda-installed python packages in the site-packages of the prefix.

        Python packages not handled by conda are installed via other means,
        like using pip or using python setup.py develop for local development.

        Packages found that are not handled by conda are converted into a
        prefix record and handled in memory.

        Packages clobbering conda packages (i.e. the conda-meta record) are
        removed from the in memory representation.
        """
        python_pkg_record = self._python_pkg_record

        if not python_pkg_record:
            return {}

        site_packages_dir = get_python_site_packages_short_path(
            python_pkg_record.version
        )
        site_packages_path = self.prefix_path / win_path_ok(site_packages_dir)

        if not site_packages_path.is_dir():
            return {}

        # Get anchor files for corresponding conda (handled) python packages
        prefix_graph = PrefixGraph(self.iter_records())
        python_records = prefix_graph.all_descendants(python_pkg_record)
        conda_python_packages = get_conda_anchor_files_and_records(
            site_packages_dir, python_records
        )

        # Get all anchor files and compare against conda anchor files to find clobbered conda
        # packages and python packages installed via other means (not handled by conda)
        sp_anchor_files = get_site_packages_anchor_files(
            site_packages_path, site_packages_dir
        )
        conda_anchor_files = set(conda_python_packages)
        clobbered_conda_anchor_files = conda_anchor_files - sp_anchor_files
        non_conda_anchor_files = sp_anchor_files - conda_anchor_files

        # If there's a mismatch for anchor files between what conda expects for a package
        # based on conda-meta, and for what is actually in site-packages, then we'll delete
        # the in-memory record for the conda package.  In the future, we should consider
        # also deleting the record on disk in the conda-meta/ directory.
        for conda_anchor_file in clobbered_conda_anchor_files:
            prefix_rec = self._prefix_records.pop(
                conda_python_packages[conda_anchor_file].name
            )
            try:
                extracted_package_dir = basename(prefix_rec.extracted_package_dir)
            except AttributeError:
                extracted_package_dir = "-".join(
                    (prefix_rec.name, prefix_rec.version, prefix_rec.build)
                )
            prefix_rec_json_path = (
                self.prefix_path / "conda-meta" / f"{extracted_package_dir}.json"
            )
            try:
                rm_rf(prefix_rec_json_path)
            except OSError:
                log.debug(
                    "stale information, but couldn't remove: %s", prefix_rec_json_path
                )
            else:
                log.debug("removed due to stale information: %s", prefix_rec_json_path)

        # Create prefix records for python packages not handled by conda
        new_packages = {}
        for af in non_conda_anchor_files:
            try:
                python_record = read_python_record(
                    self.prefix_path, af, python_pkg_record.version
                )
            except OSError as e:
                log.info(
                    "Python record ignored for anchor path '%s'\n  due to %s", af, e
                )
                continue
            except ValidationError:
                import sys

                exc_type, exc_value, exc_traceback = sys.exc_info()
                import traceback

                tb = traceback.format_exception(exc_type, exc_value, exc_traceback)
                log.warning(
                    "Problem reading non-conda package record at %s. Please verify that you "
                    "still need this, and if so, that this is still installed correctly. "
                    "Reinstalling this package may help.",
                    af,
                )
                log.debug("ValidationError: \n%s\n", "\n".join(tb))
                continue
            if not python_record:
                continue
            self.__prefix_records[python_record.name] = python_record
            new_packages[python_record.name] = python_record

        return new_packages

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
        env_vars_file.write_text(
            json.dumps(state, ensure_ascii=False, default=lambda x: x.__dict__)
        )

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

    for prefix_record in python_records:
        anchor_paths = tuple(fpath for fpath in prefix_record.files if matcher(fpath))
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


def get_python_version_for_prefix(prefix: os.PathLike) -> str | None:
    """
    For the given conda prefix, return the version of the Python installation
    in that prefix.
    """
    # returns a string e.g. "2.7", "3.4", "3.5" or None
    record = python_record_for_prefix(prefix)
    if record is not None:
        if record.version[3].isdigit():
            return record.version[:4]
        else:
            return record.version[:3]


def delete_prefix_from_linked_data(path: str | os.PathLike | Path) -> bool:
    """Here, path may be a complete prefix or a dist inside a prefix"""
    path = Path(path)
    for prefix, pip_interop in sorted(
        PrefixData._cache_, reverse=True, key=lambda key: key[0]
    ):
        try:
            path.relative_to(prefix)
            del PrefixData._cache_[(prefix, pip_interop)]
            return True
        except ValueError:
            # ValueError: path is not relative to prefix
            continue
    return False
