# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""
Configuration file manipulation utilities for conda.

This module provides classes and functions for working with conda configuration
files (.condarc), including reading, writing, and validating configuration keys.
"""

from __future__ import annotations

import os
import sys
from collections.abc import Sequence
from functools import cached_property
from logging import getLogger
from pathlib import Path
from shutil import copystat
from stat import S_IMODE
from threading import Lock
from typing import TYPE_CHECKING
from uuid import uuid4

from ..common.compat import on_mac, on_win
from ..common.configuration import DEFAULT_CONDARC_FILENAME

if TYPE_CHECKING:
    from collections.abc import Callable
    from typing import Any

    from ..common.configuration import Configuration

log = getLogger(__name__)
_write_lock = Lock()


def _reset_write_lock() -> None:
    global _write_lock
    _write_lock = Lock()


if hasattr(os, "register_at_fork"):
    os.register_at_fork(after_in_child=_reset_write_lock)


def _file_version(metadata: os.stat_result | None) -> tuple[int, ...]:
    if metadata is None:
        return ()
    return (
        metadata.st_dev,
        metadata.st_ino,
        metadata.st_mode,
        metadata.st_uid,
        metadata.st_gid,
        metadata.st_size,
        getattr(metadata, "st_flags", 0),
        getattr(metadata, "st_file_attributes", 0),
        metadata.st_mtime_ns,
        metadata.st_ctime_ns,
    )


def _read_file(path: Path) -> tuple[Path, str | None, os.stat_result | None]:
    """Read one file version, checking its descriptor and resolved path."""
    from .. import CondaError

    target = path.resolve()
    try:
        source = target.open()
    except FileNotFoundError:
        if path.resolve() == target and not target.exists():
            return target, None, None
    else:
        with source:
            before = os.fstat(source.fileno())
            text = source.read()
            try:
                current = target.stat()
            except FileNotFoundError:
                current = None
            resolved = path.resolve()
            after = os.fstat(source.fileno())
            # Windows stat and fstat can report different meanings of ctime.
            # Compare versions through descriptors and paths by identity only.
            if (
                resolved == target
                and current is not None
                and os.path.samestat(after, current)
                and _file_version(before) == _file_version(after)
            ):
                return target, text, after

    raise CondaError(
        f"Cannot read condarc file at {path}: file changed while reading. "
        "Read the file again before retrying."
    )


def _register_enum_representers() -> None:
    """Register YAML representers for conda enum types.

    This function registers custom YAML representers for all conda enum types
    to ensure they are serialized as strings rather than complex objects.

    This is called once at module load time to ensure representers are available
    before any YAML serialization occurs.
    """
    from ruamel.yaml.representer import RoundTripRepresenter

    from ..base.constants import (
        ChannelPriority,
        DepsModifier,
        PathConflict,
        SafetyChecks,
        SatSolverChoice,
        UpdateModifier,
    )

    def enum_representer(dumper, data):
        return dumper.represent_str(str(data))

    # Register each enum type individually (base Enum class registration doesn't work)
    for enum_class in (
        SafetyChecks,
        PathConflict,
        DepsModifier,
        UpdateModifier,
        ChannelPriority,
        SatSolverChoice,
    ):
        RoundTripRepresenter.add_representer(enum_class, enum_representer)


# Register enum representers once at module load time
_register_enum_representers()


class _MissingSentinel:
    """Sentinel value to indicate a missing configuration key.

    This is used by ConfigurationFile.get_key() to distinguish between a key that
    doesn't exist and a key that exists but has a None value.
    """

    def __repr__(self):
        return "<MISSING>"

    def __bool__(self):
        return False

    def __eq__(self, other):
        return isinstance(other, _MissingSentinel)

    def __hash__(self):
        return hash(_MissingSentinel)


MISSING = _MissingSentinel()


class ParameterTypeGroups:
    """
    Groups configuration parameters by their parameter type.

    Organizes configuration parameters from a Configuration instance into sequence
    and map parameters, handling both regular and plugin parameters separately.

    This is primarily used by ConfigurationFile to efficiently determine which operations
    are valid for different configuration keys.
    """

    def __init__(self, context: Configuration) -> None:
        """
        Initialize ParameterTypeGroups by grouping parameters by type.

        Args:
            context: Configuration instance containing configuration parameters.
        """
        from ..common.iterators import groupby_to_dict as groupby

        self._grouped_parameter = groupby(
            lambda p: context.describe_parameter(p)["parameter_type"],
            context.list_parameters(),
        )

        # Handle plugin parameters if the context has a plugins attribute
        if hasattr(context, "plugins"):
            self._plugin_grouped_parameters = groupby(
                lambda p: context.plugins.describe_parameter(p)["parameter_type"],
                context.plugins.list_parameters(),
            )
        else:
            self._plugin_grouped_parameters = {}

    @cached_property
    def sequence_parameters(self) -> list[str]:
        """List of sequence parameter names."""
        return self._grouped_parameter.get("sequence", [])

    @cached_property
    def plugin_sequence_parameters(self) -> list[str]:
        """List of plugin sequence parameter names."""
        return self._plugin_grouped_parameters.get("sequence", [])

    @cached_property
    def map_parameters(self) -> list[str]:
        """List of map parameter names."""
        return self._grouped_parameter.get("map", [])

    @cached_property
    def plugin_map_parameters(self) -> list[str]:
        """List of plugin map parameter names."""
        return self._plugin_grouped_parameters.get("map", [])


def validate_provided_parameters(
    parameters: Sequence[str],
    plugin_parameters: Sequence[str],
    context: Configuration,
) -> None:
    """
    Validate that provided parameters exist in the configuration context.

    Compares the provided parameters with the available parameters in the context
    and raises an error if any are invalid.

    Args:
        parameters: Regular parameter names to validate.
        plugin_parameters: Plugin parameter names to validate.
        context: Configuration instance containing available parameters.

    Raises:
        ArgumentError: If any provided parameters are not valid.
    """
    from ..common.io import dashlist
    from ..exceptions import ArgumentError

    all_names = context.list_parameters(aliases=True)

    # Handle plugin parameters if the context has a plugins attribute
    if hasattr(context, "plugins"):
        all_plugin_names = context.plugins.list_parameters()
    else:
        all_plugin_names = []

    not_params = set(parameters) - set(all_names)
    not_plugin_params = set(plugin_parameters) - set(all_plugin_names)

    if not_params or not_plugin_params:
        not_plugin_params = {f"plugins.{name}" for name in not_plugin_params}
        error_params = not_params | not_plugin_params
        raise ArgumentError(
            f"Invalid configuration parameters: {dashlist(error_params)}"
        )


class ConfigurationFile:
    """
    Represents and manipulates a conda configuration (.condarc) file.

    Provides methods to read, write, and modify configuration files while
    validating keys and maintaining proper structure.

    Can be used as a context manager for atomic edits:

        with ConfigurationFile.from_user_condarc() as config:
            config.set_key("channels", ["conda-forge"])
            config.add("channels", "defaults")
        # File is automatically written when exiting the context
    """

    def __init__(
        self,
        path: str | os.PathLike[str] | Path | None = None,
        context: Configuration | None = None,
        content: dict[str, Any] | None = None,
        warning_handler: Callable[[str], None] | None = None,
    ) -> None:
        self._path = path
        self._content = content
        self._read_state: tuple[Path, Path, str | None, tuple[int, ...]] | None = None

        self._context = context
        self._context_params: ParameterTypeGroups | None = None

        self.warning_handler = warning_handler or (lambda msg: None)

    @classmethod
    def from_user_condarc(
        cls, context: Configuration | None = None
    ) -> ConfigurationFile:
        """
        Create a ConfigurationFile instance for the default user .condarc file.

        Args:
            context: Optional Configuration instance. If None, uses the global context.

        Returns:
            ConfigurationFile instance configured for the user's .condarc file.
        """
        from ..base.context import user_rc_path

        return cls(path=user_rc_path, context=context)

    @classmethod
    def from_system_condarc(
        cls, context: Configuration | None = None
    ) -> ConfigurationFile:
        """
        Create a ConfigurationFile instance for the system .condarc file.

        Args:
            context: Optional Configuration instance. If None, uses the global context.

        Returns:
            ConfigurationFile instance configured for the system .condarc file.
        """
        from ..base.context import sys_rc_path

        return cls(path=sys_rc_path, context=context)

    @classmethod
    def from_env_condarc(
        cls,
        prefix: str | os.PathLike[str] | Path | None = None,
        context: Configuration | None = None,
    ) -> ConfigurationFile:
        """
        Create a ConfigurationFile instance for an environment-specific .condarc file.

        Environment-specific .condarc files are located at `{prefix}/.condarc` and allow
        per-environment configuration overrides.

        Args:
            prefix: Path to the conda environment. If None, uses $CONDA_PREFIX or sys.prefix.
            context: Optional Configuration instance. If None, uses the global context.

        Returns:
            ConfigurationFile instance configured for the environment's .condarc file.
        """
        if prefix is None:
            prefix = os.environ.get("CONDA_PREFIX", sys.prefix)

        return cls(path=Path(prefix) / DEFAULT_CONDARC_FILENAME, context=context)

    def __enter__(self) -> ConfigurationFile:
        """Enter the context manager."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Exit the context manager and write changes if no exception occurred."""
        if exc_type is None:
            self.write()

    @property
    def path(self) -> str | os.PathLike[str] | Path:
        """
        Get the path to the configuration file.

        Returns:
            Path to the configuration file.

        Raises:
            AttributeError: If path has not been set.
        """
        if self._path is None:
            raise AttributeError("Configuration file path has not been set")

        return self._path

    @path.setter
    def path(self, path: str | os.PathLike[str] | Path) -> None:
        """
        Set the path to the configuration file.

        Args:
            path: Path to the configuration file.
        """
        self._path = path

    @property
    def context(self) -> Configuration:
        """
        Get the context instance.

        If no context was provided during initialization, falls back to the global
        conda context singleton. This lazy import is necessary to avoid circular
        dependencies at module load time.

        Returns:
            Configuration instance.
        """
        if self._context is None:
            # Import the global context singleton
            # This is imported lazily to avoid circular import issues
            from ..base.context import context

            self._context = context

        return self._context

    @property
    def context_params(self) -> ParameterTypeGroups:
        if self._context_params is None:
            self._context_params = ParameterTypeGroups(self.context)
        return self._context_params

    @property
    def content(self) -> dict[str, Any]:
        """
        Get the configuration content, reading from file if needed.

        Returns:
            Dictionary containing configuration content.
        """
        if self._content is None:
            self.read()

        return self._content

    def read(self, path: str | os.PathLike[str] | Path | None = None) -> dict[str, Any]:
        """
        Read configuration content from file.

        Args:
            path: Optional path to read from. If None, uses the instance path.

        Returns:
            Dictionary containing configuration content.
        """
        from ..common.serialize import yaml

        path = Path(path or self._path)

        target, text, metadata = _read_file(path)

        self._content = (yaml.read(text=text) or {}) if text is not None else {}
        self._read_state = (path.absolute(), target, text, _file_version(metadata))
        return self._content

    def write(self, path: str | os.PathLike[str] | Path | None = None) -> None:
        """
        Write configuration content to file.

        Args:
            path: Optional path to write to. If None, uses the instance path.

        Raises:
            CondaError: If the file cannot be written.
        """
        from .. import CondaError
        from ..common.serialize import yaml
        from ..gateways.disk.lock import lock

        path = Path(path or self._path)
        source_fd = None
        temporary = None
        temporary_metadata = None

        def conflict(when: str) -> CondaError:
            return CondaError(
                f"Cannot write to condarc file at {path}: file changed {when}. "
                "Read the file again before retrying."
            )

        try:
            text = yaml.write(self.content)
            target, previous_text, metadata = _read_file(path)
            state = (target, previous_text, _file_version(metadata))
            if self._read_state is not None:
                read_path, *read_state = self._read_state
                if (
                    read_path == path.absolute() or read_state[0] == target
                ) and state != tuple(read_state):
                    raise conflict("after reading")
            if text == previous_text:
                self._read_state = (path.absolute(), *state)
                return

            def source_changed() -> bool:
                current_target, current_text, current_metadata = _read_file(path)
                return state != (
                    current_target,
                    current_text,
                    _file_version(current_metadata),
                )

            parent_metadata = target.parent.stat()
            lock_path = target.with_name(f"{target.name}.lock")
            # POSIX record locks are per process. Keep all opens and closes of
            # the persistent lock file inside the thread lock as well.
            with (
                _write_lock,
                lock_path.open("a+") as lock_file,
                lock(lock_file, required=True),
            ):
                lock_metadata = os.fstat(lock_file.fileno())

                def paths_changed() -> bool:
                    try:
                        return not (
                            os.path.samestat(parent_metadata, target.parent.stat())
                            and os.path.samestat(lock_metadata, lock_path.lstat())
                        )
                    except FileNotFoundError:
                        return True

                if paths_changed() or source_changed():
                    raise conflict("while waiting to write")
                if metadata is not None:
                    write_fd = os.open(target, os.O_WRONLY)
                    os.close(write_fd)
                    if on_mac:
                        source_fd = os.open(target, os.O_RDONLY)
                        if _file_version(os.fstat(source_fd)) != _file_version(
                            metadata
                        ):
                            raise conflict("while writing")

                candidate = target.with_name(f".{target.name}.{uuid4().hex}.tmp")
                if metadata is None:
                    mode = 0o666
                else:
                    mode = 0 if on_mac else S_IMODE(metadata.st_mode)
                fd = os.open(candidate, os.O_CREAT | os.O_EXCL | os.O_WRONLY, mode)
                temporary = candidate
                temporary_metadata = os.fstat(fd)
                with os.fdopen(fd, "w") as stream:
                    if metadata is not None:
                        if on_mac:
                            from ..common._os.osx import copy_acl

                            copy_acl(source_fd, stream.fileno())
                        if hasattr(os, "chown"):
                            if (
                                temporary_metadata.st_uid,
                                temporary_metadata.st_gid,
                            ) != (metadata.st_uid, metadata.st_gid):
                                os.chown(temporary, metadata.st_uid, metadata.st_gid)
                        copystat(target, temporary)
                        if source_changed():
                            raise conflict("while writing")
                    stream.write(text)
                    stream.flush()
                    os.fsync(stream.fileno())
                    staged_metadata = os.fstat(stream.fileno())

                _, staged_text, closed_metadata = _read_file(temporary)
                # Windows can finalize timestamps when the writing handle closes.
                # Contents, identity, and access metadata must still match.
                version_end = -2 if on_win else None
                if (
                    staged_text != text
                    or closed_metadata is None
                    or _file_version(staged_metadata)[:version_end]
                    != _file_version(closed_metadata)[:version_end]
                ):
                    raise conflict("while writing")
                staged_metadata = closed_metadata
                with temporary.open() as staged:
                    if (
                        paths_changed()
                        or source_changed()
                        or not os.path.samestat(staged_metadata, temporary.lstat())
                        or _file_version(os.fstat(staged.fileno()))
                        != _file_version(staged_metadata)
                    ):
                        raise conflict("while writing")
                if source_fd is not None:
                    os.close(source_fd)
                    source_fd = None
                os.replace(temporary, target)
                temporary = None
                self._read_state = (
                    path.absolute(),
                    target,
                    text,
                    _file_version(staged_metadata),
                )
                # Rename may change ctime. Only refresh it from our staged file,
                # never from a replacement or different contents written later.
                try:
                    committed_target, committed_text, committed_metadata = _read_file(
                        path
                    )
                except (OSError, CondaError):
                    pass
                else:
                    if (
                        committed_target == target
                        and committed_text == text
                        and committed_metadata is not None
                        and _file_version(staged_metadata)[:-1]
                        == _file_version(committed_metadata)[:-1]
                    ):
                        self._read_state = (
                            path.absolute(),
                            target,
                            text,
                            _file_version(committed_metadata),
                        )
        except OSError as e:
            raise CondaError(f"Cannot write to condarc file at {path}\nCaused by {e!r}")
        finally:
            if source_fd is not None:
                os.close(source_fd)
            if temporary is not None:
                try:
                    if temporary_metadata is not None and os.path.samestat(
                        temporary_metadata, temporary.lstat()
                    ):
                        temporary.unlink()
                except FileNotFoundError:
                    pass

    def key_exists(self, key: str) -> bool:
        """
        Check if a configuration key is valid.

        Args:
            key: Configuration key to check.

        Returns:
            True if the key is valid, False otherwise.
        """
        first, *rest = key.split(".")

        # Handle plugin parameters if the context has a plugins attribute
        if (
            first == "plugins"
            and len(rest) > 0
            and hasattr(self.context, "plugins")
            and rest[0] in self.context.plugins.list_parameters()
        ):
            return True

        if first not in self.context.list_parameters():
            exists = bool(self.context.name_for_alias(first))
            if not exists:
                self.warning_handler(f"Unknown key: {key!r}")
            return exists

        return True

    def add(self, key: str, item: Any, prepend: bool = False) -> None:
        """
        Add an item to a sequence configuration parameter.

        Args:
            key: Configuration key name (may contain dots for nested keys).
            item: Item to add to the sequence.
            prepend: If True, add to the beginning; if False, add to the end.

        Raises:
            CondaValueError: If the key is not a known sequence parameter.
            CouldntParseError: If the key should be a list but isn't.
        """
        from ..exceptions import CondaValueError, CouldntParseError

        key, subkey = key.split(".", 1) if "." in key else (key, None)

        if key in self.context_params.sequence_parameters:
            arglist = self.content.setdefault(key, [])
        elif (
            key == "plugins"
            and subkey in self.context_params.plugin_sequence_parameters
        ):
            arglist = self.content.setdefault("plugins", {}).setdefault(subkey, [])
        elif key in self.context_params.map_parameters:
            arglist = self.content.setdefault(key, {}).setdefault(subkey, [])
        elif key in self.context_params.plugin_map_parameters:
            arglist = self.content.setdefault("plugins", {}).setdefault(subkey, {})
        else:
            raise CondaValueError(f"Key '{key}' is not a known sequence parameter.")

        if not (isinstance(arglist, Sequence) and not isinstance(arglist, str)):
            bad = self.content[key].__class__.__name__
            raise CouldntParseError(f"key {key!r} should be a list, not {bad}.")

        if item in arglist:
            # Right now, all list keys should not contain duplicates
            location = "top" if prepend else "bottom"
            message_key = key + "." + subkey if subkey is not None else key
            message = f"Warning: '{item}' already in '{message_key}' list, moving to the {location}"

            if subkey is None:
                arglist = self.content[key] = [p for p in arglist if p != item]
            else:
                arglist = self.content[key][subkey] = [p for p in arglist if p != item]

            self.warning_handler(msg=message)

        arglist.insert(0 if prepend else len(arglist), item)

    def get_key(
        self,
        key: str,
    ) -> tuple[str, Any | _MissingSentinel]:
        """
        Get a configuration value by key.

        Args:
            key: Configuration key name (may contain dots for nested keys).

        Returns:
            Tuple of (key, value) or (key, MISSING) if key doesn't exist.
        """
        key_parts = key.split(".")

        if not self.key_exists(key):
            return key, MISSING

        if alias := self.context.name_for_alias(key):
            key = alias
            key_parts = alias.split(".")

        sub_config = self.content
        try:
            for index, part in enumerate(key_parts):
                remainder = ".".join(key_parts[index:])
                if remainder in sub_config:
                    return key, sub_config[remainder]
                sub_config = sub_config[part]
        except KeyError:
            pass
        else:
            return key, sub_config

        return key, MISSING

    def set_key(self, key: str, item: Any) -> None:
        """
        Set a configuration value for a primitive or map parameter.

        Args:
            key: Configuration key name (may contain dots for nested keys).
            item: Value to set.

        Raises:
            CondaKeyError: If the key is unknown or invalid.
        """
        from ..exceptions import CondaKeyError

        if not self.key_exists(key):
            raise CondaKeyError(key, "unknown parameter")

        if aliased := self.context.name_for_alias(key):
            log.warning(
                "Key %s is an alias of %s; setting value with latter", key, aliased
            )
            key = aliased

        first, *rest = key.split(".")

        if first == "plugins" and hasattr(self.context, "plugins"):
            base_context = self.context.plugins
            base_config = self.content.setdefault("plugins", {})
            parameter_name, *rest = rest
        else:
            base_context = self.context
            base_config = self.content
            parameter_name = first

        parameter_type = base_context.describe_parameter(parameter_name)[
            "parameter_type"
        ]

        if parameter_type == "primitive" and len(rest) == 0:
            base_config[parameter_name] = base_context.typify_parameter(
                parameter_name, item, "--set parameter"
            )

        elif parameter_type == "map" and rest:
            base_config.setdefault(parameter_name, {})[".".join(rest)] = item

        else:
            raise CondaKeyError(key, "invalid parameter")

    def remove_item(self, key: str, item: Any) -> None:
        """
        Remove an item from a sequence configuration parameter.

        Args:
            key: Configuration key name.
            item: Item to remove from the sequence.

        Raises:
            CondaKeyError: If the key is unknown, undefined, or the item is not present.
        """
        from ..exceptions import CondaKeyError

        first, *rest = key.split(".")

        if first == "plugins" and hasattr(self.context, "plugins"):
            base_context = self.context.plugins
            base_config = self.content.setdefault("plugins", {})
            parameter_name = rest[0]
            rest = []
        else:
            base_context = self.context
            base_config = self.content
            parameter_name = first

        try:
            parameter_type = base_context.describe_parameter(parameter_name)[
                "parameter_type"
            ]
        except KeyError:
            # KeyError: key_parts[0] is an unknown parameter
            raise CondaKeyError(key, "unknown parameter")

        if parameter_type == "sequence" and len(rest) == 0:
            if parameter_name not in base_config:
                if parameter_name != "channels":
                    raise CondaKeyError(key, "undefined in config")
                self.content[parameter_name] = ["defaults"]

            if item not in base_config[parameter_name]:
                raise CondaKeyError(
                    parameter_name, f"value {item!r} not present in config"
                )
            base_config[parameter_name] = [
                i for i in base_config[parameter_name] if i != item
            ]
        else:
            raise CondaKeyError(key, "invalid parameter")

    def clear_key(self, key: str) -> None:
        """
        Clear all values from a sequence configuration parameter.

        The key remains explicitly configured with an empty list. This differs
        from ``remove_key()``, which removes the key entirely and may allow a
        value from another configuration source or a default to take effect.

        Args:
            key: Sequence configuration key name.

        Raises:
            CondaKeyError: If the key is unknown or is not a sequence parameter.
            CouldntParseError: If the configured value is not a sequence.
        """
        from ..exceptions import CondaKeyError, CouldntParseError

        if not self.key_exists(key):
            raise CondaKeyError(key, "unknown parameter")

        alias_key = None
        if aliased := self.context.name_for_alias(key):
            log.warning(
                "Key %s is an alias of %s; clearing value with latter",
                key,
                aliased,
            )
            alias_key = key
            key = aliased

        first, *rest = key.split(".")

        if first == "plugins" and hasattr(self.context, "plugins"):
            base_context = self.context.plugins
            base_config = self.content.setdefault("plugins", {})
            parameter_name, *rest = rest
        else:
            base_context = self.context
            base_config = self.content
            parameter_name = first

        try:
            parameter_type = base_context.describe_parameter(parameter_name)[
                "parameter_type"
            ]
        except KeyError:
            raise CondaKeyError(key, "unknown parameter")

        if parameter_type != "sequence" or rest:
            raise CondaKeyError(key, "invalid parameter")

        current_value = base_config.get(parameter_name, MISSING)
        if current_value is not MISSING and not (
            isinstance(current_value, Sequence) and not isinstance(current_value, str)
        ):
            bad_type = current_value.__class__.__name__
            raise CouldntParseError(f"key {key!r} should be a list, not {bad_type}.")

        if alias_key is not None:
            self.content.pop(alias_key, None)

        base_config[parameter_name] = []

    def remove_key(self, key: str) -> None:
        """
        Remove a configuration key entirely.

        Args:
            key: Configuration key name (may contain dots for nested keys).

        Raises:
            CondaKeyError: If the key is undefined in the config.
        """
        from ..exceptions import CondaKeyError

        key_parts = key.split(".")

        sub_config = self.content
        try:
            for index, part in enumerate(key_parts[:-1]):
                remainder = ".".join(key_parts[index:])
                if remainder in sub_config:
                    del sub_config[remainder]
                    return
                sub_config = sub_config[part]
            del sub_config[key_parts[-1]]
        except KeyError:
            # KeyError: part not found, nothing to remove, but maybe user passed an alias?
            if alias := self.context.name_for_alias(key):
                try:
                    return self.remove_key(alias)
                except CondaKeyError:
                    pass  # raise with originally passed key
            raise CondaKeyError(key, "undefined in config")
