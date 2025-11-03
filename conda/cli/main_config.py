# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""CLI implementation for `conda config`.

Allows for programmatically interacting with conda's configuration files (e.g., `~/.condarc`).
"""

from __future__ import annotations

import os
import sys
from argparse import SUPPRESS
from collections.abc import Mapping, Sequence
from functools import cached_property
from itertools import chain
from logging import getLogger
from os.path import isfile, join
from pathlib import Path
from textwrap import wrap
from typing import TYPE_CHECKING

from ruamel.yaml.representer import RoundTripRepresenter

from ..common.configuration import DEFAULT_CONDARC_FILENAME
from ..common.iterators import groupby_to_dict as groupby
from ..exceptions import CondaKeyError, CondaValueError, CouldntParseError

if TYPE_CHECKING:
    from argparse import ArgumentParser, Namespace, _SubParsersAction
    from collections.abc import Callable
    from typing import Any

    from ..base.context import Context

log = getLogger(__name__)

MISSING = object()


def add_enum_representers() -> None:
    """Register YAML representers for conda enum types."""
    from ..base.constants import (
        ChannelPriority,
        DepsModifier,
        PathConflict,
        SafetyChecks,
        SatSolverChoice,
        UpdateModifier,
    )

    # Add representers for enums.
    # Because a representer cannot be added for the base Enum class (it must be added for
    # each specific Enum subclass - and because of import rules), I don't know of a better
    # location to do this.
    def enum_representer(dumper, data):
        return dumper.represent_str(str(data))

    RoundTripRepresenter.add_representer(SafetyChecks, enum_representer)
    RoundTripRepresenter.add_representer(PathConflict, enum_representer)
    RoundTripRepresenter.add_representer(DepsModifier, enum_representer)
    RoundTripRepresenter.add_representer(UpdateModifier, enum_representer)
    RoundTripRepresenter.add_representer(ChannelPriority, enum_representer)
    RoundTripRepresenter.add_representer(SatSolverChoice, enum_representer)


add_enum_representers()


def configure_parser(sub_parsers: _SubParsersAction, **kwargs) -> ArgumentParser:
    from ..auxlib.ish import dals
    from ..base.constants import CONDA_HOMEPAGE_URL
    from ..base.context import context, sys_rc_path, user_rc_path
    from ..common.constants import NULL
    from .helpers import add_parser_json, add_parser_prefix_to_group

    escaped_user_rc_path = user_rc_path.replace("%", "%%")
    escaped_sys_rc_path = sys_rc_path.replace("%", "%%")

    summary = "Modify configuration values in .condarc."
    description = dals(
        f"""
        {summary}

        This is modeled after the git config command.  Writes to the user .condarc
        file ({escaped_user_rc_path}) by default. Use the
        --show-sources flag to display all identified configuration locations on
        your computer.

        """
    )
    epilog = dals(
        f"""
        See `conda config --describe` or {CONDA_HOMEPAGE_URL}/docs/config.html
        for details on all the options that can go in .condarc.

        Examples:

        Display all configuration values as calculated and compiled::

            conda config --show

        Display all identified configuration sources::

            conda config --show-sources

        Print the descriptions of all available configuration
        options to your command line::

            conda config --describe

        Print the description for the "channel_priority" configuration
        option to your command line::

            conda config --describe channel_priority

        Add the conda-canary channel::

            conda config --add channels conda-canary

        Set the output verbosity to level 3 (highest) for
        the current activate environment::

            conda config --set verbosity 3 --env

        Add the 'conda-forge' channel as a backup to 'defaults'::

            conda config --append channels conda-forge

        """
    )

    p = sub_parsers.add_parser(
        "config",
        help=summary,
        description=description,
        epilog=epilog,
        **kwargs,
    )
    add_parser_json(p)

    # TODO: use argparse.FileType
    config_file_location_group = p.add_argument_group(
        "Config File Location Selection",
        f"Without one of these flags, the user config file at '{escaped_user_rc_path}' is used.",
    )
    location = config_file_location_group.add_mutually_exclusive_group()
    location.add_argument(
        "--system",
        action="store_true",
        help=f"Write to the system .condarc file at '{escaped_sys_rc_path}'.",
    )
    location.add_argument(
        "--env",
        action="store_true",
        help="Write to the active conda environment .condarc file ({}). "
        "If no environment is active, write to the user config file ({})."
        "".format(
            context.active_prefix or "<no active environment>",
            escaped_user_rc_path,
        ),
    )
    location.add_argument("--file", action="store", help="Write to the given file.")
    add_parser_prefix_to_group(location)

    # XXX: Does this really have to be mutually exclusive. I think the below
    # code will work even if it is a regular group (although combination of
    # --add and --remove with the same keys will not be well-defined).
    _config_subcommands = p.add_argument_group("Config Subcommands")
    config_subcommands = _config_subcommands.add_mutually_exclusive_group()
    config_subcommands.add_argument(
        "--show",
        nargs="*",
        default=None,
        help="Display configuration values as calculated and compiled. "
        "If no arguments given, show information for all configuration values.",
    )
    config_subcommands.add_argument(
        "--show-sources",
        action="store_true",
        help="Display all identified configuration sources.",
    )
    config_subcommands.add_argument(
        "--validate",
        action="store_true",
        help="Validate all configuration sources. Iterates over all .condarc files "
        "and checks for parsing errors.",
    )
    config_subcommands.add_argument(
        "--describe",
        nargs="*",
        default=None,
        help="Describe given configuration parameters. If no arguments given, show "
        "information for all configuration parameters.",
    )
    config_subcommands.add_argument(
        "--write-default",
        action="store_true",
        help="Write the default configuration to a file. "
        "Equivalent to `conda config --describe > ~/.condarc`.",
    )

    _config_modifiers = p.add_argument_group("Config Modifiers")
    config_modifiers = _config_modifiers.add_mutually_exclusive_group()
    config_modifiers.add_argument(
        "--get",
        nargs="*",
        action="store",
        help="Get a configuration value.",
        default=None,
        metavar="KEY",
    )
    config_modifiers.add_argument(
        "--append",
        nargs=2,
        action="append",
        help="""Add one configuration value to the end of a list key.""",
        default=[],
        metavar=("KEY", "VALUE"),
    )
    config_modifiers.add_argument(
        "--prepend",
        "--add",
        nargs=2,
        action="append",
        help="""Add one configuration value to the beginning of a list key.""",
        default=[],
        metavar=("KEY", "VALUE"),
    )
    config_modifiers.add_argument(
        "--set",
        nargs=2,
        action="append",
        help="""Set a boolean or string key.""",
        default=[],
        metavar=("KEY", "VALUE"),
    )
    config_modifiers.add_argument(
        "--remove",
        nargs=2,
        action="append",
        help="""Remove a configuration value from a list key.
                This removes all instances of the value.""",
        default=[],
        metavar=("KEY", "VALUE"),
    )
    config_modifiers.add_argument(
        "--remove-key",
        action="append",
        help="""Remove a configuration key (and all its values).""",
        default=[],
        metavar="KEY",
    )
    config_modifiers.add_argument(
        "--stdin",
        action="store_true",
        help="Apply configuration information given in yaml format piped through stdin.",
    )

    p.add_argument(
        "-f",
        "--force",
        action="store_true",
        default=NULL,
        help=SUPPRESS,  # TODO: No longer used.  Remove in a future release.
    )

    p.set_defaults(func="conda.cli.main_config.execute")

    return p


def execute(args: Namespace, parser: ArgumentParser) -> int:
    from .. import CondaError

    try:
        return execute_config(args, parser)
    except (CouldntParseError, NotImplementedError) as e:
        raise CondaError(e)


def format_dict(d):
    from ..common.compat import isiterable
    from ..common.configuration import pretty_list, pretty_map

    lines = []
    for k, v in d.items():
        if isinstance(v, Mapping):
            if v:
                lines.append(f"{k}:")
                lines.append(pretty_map(v))
            else:
                lines.append(f"{k}: {{}}")
        elif isiterable(v):
            if v:
                lines.append(f"{k}:")
                lines.append(pretty_list(v))
            else:
                lines.append(f"{k}: []")
        else:
            lines.append("{}: {}".format(k, v if v is not None else "None"))
    return lines


def parameter_description_builder(name, context=None, plugins=False):
    from ..common.serialize import json, yaml_round_trip_dump

    # Keeping this for backward-compatibility, in case no context instance is provided
    if context is None:
        from ..base.context import context

    name_prefix = "plugins." if plugins else ""

    builder = []
    details = context.describe_parameter(name)
    aliases = details["aliases"]
    string_delimiter = details.get("string_delimiter")
    element_types = details["element_types"]
    default_value_str = json.dumps(details["default_value"])

    if details["parameter_type"] == "primitive":
        builder.append(
            "{} ({})".format(
                f"{name_prefix}{name}",
                ", ".join(sorted(set(element_types))),
            )
        )
    else:
        builder.append(
            "{} ({}: {})".format(
                f"{name_prefix}{name}",
                details["parameter_type"],
                ", ".join(sorted(set(element_types))),
            )
        )

    if aliases:
        builder.append("  aliases: {}".format(", ".join(aliases)))
    if string_delimiter:
        builder.append(f"  env var string delimiter: '{string_delimiter}'")

    builder.extend("  " + line for line in wrap(details["description"], 70))

    builder.append("")
    builder = ["# " + line for line in builder]

    # If we are dealing with a plugin parameter, we need to nest it
    # instead of having it at the top level (YAML-wise).
    if plugins:
        yaml_content = yaml_round_trip_dump(
            {"plugins": {name: json.loads(default_value_str)}}
        )
    else:
        yaml_content = yaml_round_trip_dump({name: json.loads(default_value_str)})

    builder.extend(yaml_content.strip().split("\n"))

    builder = ["# " + line for line in builder]
    builder.append("")
    return builder


def describe_all_parameters(context=None, plugins=False) -> str:
    """
    Return a string with the descriptions of all available configuration

    When ``context`` has no parameters, this function returns ``""``
    """
    # Keeping this for backward-compatibility, in case no context instance is provided
    if context is None:
        from ..base.context import context

    if not context.parameter_names:
        return ""

    builder = []
    skip_categories = ("CLI-only", "Hidden and Undocumented")
    for category, parameter_names in context.category_map.items():
        if category in skip_categories:
            continue
        builder.append("# ######################################################")
        builder.append(f"# ## {category:^48} ##")
        builder.append("# ######################################################")
        builder.append("")
        builder.extend(
            chain.from_iterable(
                parameter_description_builder(name, context, plugins=plugins)
                for name in parameter_names
            )
        )
        builder.append("")
    return "\n".join(builder)


def print_config_item(key, value):
    stdout_write = getLogger("conda.stdout").info
    if isinstance(value, (dict,)):
        for k, v in value.items():
            print_config_item(key + "." + k, v)
    elif isinstance(value, (bool, int, str)):
        stdout_write(" ".join(("--set", key, str(value))))
    elif isinstance(value, (list, tuple)):
        # Note, since `conda config --add` prepends, print `--add` commands in
        # reverse order (using repr), so that entering them in this order will
        # recreate the same file.
        numitems = len(value)
        for q, item in enumerate(reversed(value)):
            if key == "channels" and q in (0, numitems - 1):
                stdout_write(
                    " ".join(
                        (
                            "--add",
                            key,
                            repr(item),
                            "  # lowest priority" if q == 0 else "  # highest priority",
                        )
                    )
                )
            else:
                stdout_write(" ".join(("--add", key, repr(item))))


class ContextParameters:
    """
    Groups configuration parameters by their parameter type.

    Organizes configuration parameters from context into sequence and map parameters,
    handling both regular and plugin parameters separately.
    """

    def __init__(self, context: Context) -> None:
        """
        Initialize ContextParameters by grouping parameters by type.

        :param context: Context instance containing configuration parameters.
        """
        self.__grouped_parameter = groupby(
            lambda p: context.describe_parameter(p)["parameter_type"],
            context.list_parameters(),
        )

        self.__plugin_grouped_parameters = groupby(
            lambda p: context.plugins.describe_parameter(p)["parameter_type"],
            context.plugins.list_parameters(),
        )

    @cached_property
    def sequence_parameters(self) -> list[str]:
        """List of sequence parameter names."""
        return self.__grouped_parameter["sequence"]

    @cached_property
    def plugin_sequence_parameters(self) -> list[str]:
        """List of plugin sequence parameter names."""
        return self.__plugin_grouped_parameters.get("sequence", [])

    @cached_property
    def map_parameters(self) -> list[str]:
        """List of map parameter names."""
        return self.__grouped_parameter["map"]

    @cached_property
    def plugin_map_parameters(self) -> list[str]:
        """List of plugin map parameter names."""
        return self.__plugin_grouped_parameters.get("map", [])

    @staticmethod
    def validate_provided_parameters(
        parameters: Sequence[str], plugin_parameters: Sequence[str], context: Context
    ) -> None:
        """
        Compares the provided parameters with the available parameters.

        :raises:
            ArgumentError: If the provided parameters are not valid.
        """
        from ..common.io import dashlist
        from ..exceptions import ArgumentError

        all_names = context.list_parameters(aliases=True)
        all_plugin_names = context.plugins.list_parameters()

        not_params = set(parameters) - set(all_names)
        not_plugin_params = set(plugin_parameters) - set(all_plugin_names)

        if not_params or not_plugin_params:
            not_plugin_params = {f"plugins.{name}" for name in not_plugin_params}
            error_params = not_params | not_plugin_params
            raise ArgumentError(
                f"Invalid configuration parameters: {dashlist(error_params)}"
            )


class CondaRC:
    """
    Represents and manipulates a conda configuration (.condarc) file.

    Provides methods to read, write, and modify configuration files while
    validating keys and maintaining proper structure.
    """

    def __init__(
        self,
        path: str | os.PathLike[str] | Path | None = None,
        context: Context | None = None,
        content: dict[str, Any] | None = None,
        warning_handler: Callable[[str], None] | None = None,
    ) -> None:
        self.__path = path
        self.__content = content

        self.__context = context
        self.__context_params = ContextParameters(self.context)

        self.warning_handler = warning_handler or (lambda msg: None)

    @property
    def path(self) -> str | os.PathLike[str] | Path:
        """
        Get the path to the configuration file.

        :returns: Path to the configuration file.
        :raises AttributeError: If path has not been set.
        """
        if self.__path is None:
            raise AttributeError("Condarc. has not been set")

        return self.__path

    @path.setter
    def path(self, path: str | os.PathLike[str] | Path) -> None:
        """
        Set the path to the configuration file.

        :param path: Path to the configuration file.
        """
        self.__path = path

    @property
    def context(self) -> Context:
        """
        Get the context instance, initializing it if needed.

        :returns: Context instance.
        """
        if self.__context is None:
            from ..base.context import context

            self.__context = context

        return self.__context

    @property
    def context_params(self) -> ContextParameters:
        return self.__context_params

    @property
    def content(self) -> dict[str, Any]:
        """
        Get the configuration content, reading from file if needed.

        :returns: Dictionary containing configuration content.
        """
        if self.__content is None:
            self.read()

        return self.__content

    def read(self, path: str | os.PathLike[str] | Path | None = None) -> dict[str, Any]:
        """
        Read configuration content from file.

        :param path: Optional path to read from. If None, uses the instance path.
        :returns: Dictionary containing configuration content.
        """
        from ..common.serialize import yaml_round_trip_load

        path = Path(path or self.__path)

        try:
            self.__content = (
                yaml_round_trip_load(Path(path or self.__path).read_text()) or {}
            )
        except FileNotFoundError:
            self.__content = {}

        return self.__content

    def write(self, path: str | os.PathLike[str] | Path | None = None) -> None:
        """
        Write configuration content to file.

        :param path: Optional path to write to. If None, uses the instance path.
        :raises CondaError: If the file cannot be written.
        """
        from .. import CondaError
        from ..common.serialize import yaml_round_trip_dump

        path: Path = Path(path or self.__path)
        try:
            path.write_text(yaml_round_trip_dump(self.content))
        except OSError as e:
            raise CondaError(f"Cannot write to condarc file at {path}\nCaused by {e!r}")

    def key_exists(self, key: str) -> bool:
        """
        Check if a configuration key is valid.

        :param key: Configuration key to check.
        :returns: True if the key is valid, False otherwise.
        """
        first, *rest = key.split(".")
        if (
            first == "plugins"
            and len(rest) > 0
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

        :param key: Configuration key name (may contain dots for nested keys).
        :param item: Item to add to the sequence.
        :param prepend: If True, add to the beginning; if False, add to the end.
        :raises CondaValueError: If the key is not a known sequence parameter.
        :raises CouldntParseError: If the key should be a list but isn't.
        """
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
    ) -> tuple[str, Any]:
        """
        Get a configuration value by key.

        :param key: Configuration key name (may contain dots for nested keys).
        :returns: Configuration value or MISSING if key doesn't exist.
        """
        key_parts = key.split(".")

        if not self.key_exists(key):
            return key, MISSING

        if alias := self.context.name_for_alias(key):
            key = alias
            key_parts = alias.split(".")

        sub_config = self.content
        try:
            for part in key_parts:
                sub_config = sub_config[part]
        except KeyError:
            pass
        else:
            return key, sub_config

        return key, MISSING

    def set_key(self, key: str, item: Any) -> None:
        """
        Set a configuration value for a primitive or map parameter.

        :param key: Configuration key name (may contain dots for nested keys).
        :param item: Value to set.
        :raises CondaKeyError: If the key is unknown or invalid.
        """
        if not self.key_exists(key):
            raise CondaKeyError(key, "unknown parameter")

        if aliased := self.context.name_for_alias(key):
            log.warning(
                "Key %s is an alias of %s; setting value with latter", key, aliased
            )
            key = aliased

        first, *rest = key.split(".")

        if first == "plugins":
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

        elif parameter_type == "map" and len(rest) == 1:
            base_config.setdefault(parameter_name, {})[rest[0]] = item

        else:
            raise CondaKeyError(key, "invalid parameter")

    def remove_item(self, key: str, item: Any) -> None:
        """
        Remove an item from a sequence configuration parameter.

        :param key: Configuration key name.
        :param item: Item to remove from the sequence.
        :raises CondaKeyError: If the key is unknown, undefined, or the item is not present.
        """
        first, *rest = key.split(".")

        if first == "plugins":
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

    def remove_key(self, key: str) -> None:
        """
        Remove a configuration key entirely.

        :param key: Configuration key name (may contain dots for nested keys).
        :raises CondaKeyError: If the key is undefined in the config.
        """
        key_parts = key.split(".")

        sub_config = self.content
        try:
            for part in key_parts[:-1]:
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


def set_keys(*args: tuple[str, Any], path: str | os.PathLike[str] | Path) -> None:
    """
    Set multiple configuration keys in a file.

    :param args: Variable number of (key, value) tuples to set.
    :param path: Path to the configuration file.
    """
    config = CondaRC(path)
    for key, value in args:
        config.set_key(key, value)
    config.write()


def execute_config(args: Namespace, parser: ArgumentParser) -> int | None:
    """
    Execute the conda config command based on provided arguments.

    Handles various config subcommands including show, show-sources, describe,
    validate, write-default, and modification operations (add, set, remove, etc.).

    :param args: Parsed command line arguments.
    :param parser: Argument parser instance.
    """
    from .. import CondaError
    from ..base.context import (
        context,
        sys_rc_path,
        user_rc_path,
    )
    from ..common.io import timeout
    from ..common.serialize import json, yaml_round_trip_load
    from ..core.prefix_data import PrefixData

    # Override context for --file operations with --show/--describe
    if args.file and (args.show is not None or args.describe is not None):
        from ..base.context import Context

        context = Context(search_path=(args.file,), argparse_args=args)

    stdout_write = getLogger("conda.stdout").info
    stderr_write = getLogger("conda.stderr").info
    get_key_pairs = []
    json_warnings = []

    if args.show_sources:
        if context.json:
            stdout_write(
                json.dumps(
                    {
                        str(source): values
                        for source, values in context.collect_all().items()
                    },
                    sort_keys=True,
                )
            )
        else:
            lines = []
            for source, reprs in context.collect_all().items():
                lines.append(f"==> {source} <==")
                lines.extend(format_dict(reprs))
                lines.append("")
            stdout_write("\n".join(lines))
        return

    if args.show is not None:
        if args.show:
            provided_parameters = tuple(
                name for name in args.show if not name.startswith("plugins.")
            )
            provided_plugin_parameters = tuple(
                name.replace("plugins.", "")
                for name in args.show
                if name.startswith("plugins.")
            )

            ContextParameters.validate_provided_parameters(
                provided_parameters, provided_plugin_parameters, context
            )
            provided_parameters = tuple(
                dict.fromkeys(
                    context.name_for_alias(name) or name for name in provided_parameters
                )
            )

        else:
            provided_parameters = context.list_parameters()
            provided_plugin_parameters = context.plugins.list_parameters()

        d = {key: getattr(context, key) for key in provided_parameters}

        d["plugins"] = {}

        # sort to make sure "plugins" appears in the right spot
        d = {key: value for key, value in sorted(d.items())}

        for key in provided_plugin_parameters:
            value = getattr(context.plugins, key)
            if isinstance(value, Mapping):
                d["plugins"][key] = dict(value)
            elif isinstance(value, tuple) and len(value) == 0:
                d["plugins"][key] = []
            else:
                d["plugins"][key] = value

        if not d["plugins"]:
            del d["plugins"]

        if context.json:
            stdout_write(json.dumps(d, sort_keys=True))
        else:
            # Add in custom formatting
            if "custom_channels" in d:
                d["custom_channels"] = {
                    channel.name: f"{channel.scheme}://{channel.location}"
                    for channel in d["custom_channels"].values()
                }
            if "custom_multichannels" in d:
                from ..common.io import dashlist

                d["custom_multichannels"] = {
                    multichannel_name: dashlist(channels, indent=4)
                    for multichannel_name, channels in d["custom_multichannels"].items()
                }
            if "channel_settings" in d:
                ident = " " * 4
                d["channel_settings"] = tuple(
                    f"\n{ident}".join(format_dict(mapping))
                    for mapping in d["channel_settings"]
                )

            stdout_write("\n".join(format_dict(d)))
        context.validate_configuration()
        context.plugins.validate_configuration()
        return

    if args.describe is not None:
        if args.describe:
            provided_parameters = tuple(
                name for name in args.describe if not name.startswith("plugins.")
            )
            provided_plugin_parameters = tuple(
                name.replace("plugins.", "")
                for name in args.describe
                if name.startswith("plugins.")
            )
            ContextParameters.validate_provided_parameters(
                provided_parameters, provided_plugin_parameters, context
            )
            provided_parameters = tuple(
                dict.fromkeys(
                    context.name_for_alias(name) or name for name in provided_parameters
                )
            )

            if context.json:
                json_descriptions = [
                    context.describe_parameter(name) for name in provided_parameters
                ] + [
                    context.plugins.describe_parameter(name)
                    for name in provided_plugin_parameters
                ]
                stdout_write(
                    json.dumps(
                        json_descriptions,
                        sort_keys=True,
                    )
                )
            else:
                builder = []
                builder.extend(
                    chain.from_iterable(
                        parameter_description_builder(name, context)
                        for name in provided_parameters
                    )
                )
                builder.extend(
                    chain.from_iterable(
                        parameter_description_builder(
                            name, context.plugins, plugins=True
                        )
                        for name in provided_plugin_parameters
                    )
                )
                stdout_write("\n".join(builder))
        else:
            if context.json:
                skip_categories = ("CLI-only", "Hidden and Undocumented")
                provided_parameters = sorted(
                    chain.from_iterable(
                        parameter_names
                        for category, parameter_names in context.category_map.items()
                        if category not in skip_categories
                    )
                )
                stdout_write(
                    json.dumps(
                        [
                            context.describe_parameter(name)
                            for name in provided_parameters
                        ],
                        sort_keys=True,
                    )
                )
            else:
                stdout_write(describe_all_parameters(context))
                stdout_write(describe_all_parameters(context.plugins, plugins=True))
        return

    if args.validate:
        context.validate_all()
        return

    if args.system:
        rc_path = sys_rc_path
    elif args.env:
        if context.active_prefix:
            rc_path = join(context.active_prefix, DEFAULT_CONDARC_FILENAME)
        else:
            rc_path = user_rc_path
    elif args.file:
        rc_path = args.file
    elif args.prefix or args.name:
        prefix_data = PrefixData.from_context()
        prefix_data.assert_environment()
        rc_path = str(prefix_data.prefix_path / DEFAULT_CONDARC_FILENAME)
    else:
        rc_path = user_rc_path

    if args.write_default:
        if isfile(rc_path):
            with open(rc_path) as fh:
                data = fh.read().strip()
            if data:
                raise CondaError(
                    f"The file '{rc_path}' "
                    "already contains configuration information.\n"
                    "Remove the file to proceed.\n"
                    "Use `conda config --describe` to display default configuration."
                )

        with open(rc_path, "w") as fh:
            fh.write(describe_all_parameters(context))
            fh.write(describe_all_parameters(context.plugins, plugins=True))
        return

    rc_config = CondaRC(
        path=rc_path,
        context=context,
        warning_handler=lambda msg: json_warnings.append(msg)
        if context.json
        else stderr_write(msg),
    )

    # read existing condarc
    if os.path.exists(rc_path):
        rc_config.read()
    elif os.path.exists(sys_rc_path):
        # In case the considered rc file doesn't exist, fall back to the system rc
        rc_config.read(sys_rc_path)

    # Get
    if args.get is not None:
        context.validate_all()
        for key in args.get or sorted(rc_config.content.keys()):
            name, value = rc_config.get_key(key)
            if value is not MISSING:
                get_key_pairs.append((name, value))

    if args.stdin:
        content = timeout(5, sys.stdin.read)
        if not content:
            return
        try:
            # round trip load required because... we need to round trip
            parsed = yaml_round_trip_load(content)
            rc_config.content.update(parsed)
        except Exception:  # pragma: no cover
            from ..exceptions import ParseError

            raise ParseError(f"invalid yaml content:\n{content}")

    # prepend, append, add
    for arg, prepend in zip((args.prepend, args.append), (True, False)):
        for key, item in arg:
            rc_config.add(key, item, prepend=prepend)

    # Set
    for key, item in args.set:
        rc_config.set_key(key, item)

    # Remove
    for key, item in args.remove:
        rc_config.remove_item(key, item)

    # Remove Key
    for key in args.remove_key:
        rc_config.remove_key(key)

    # config.rc_keys
    if not args.get:
        rc_config.write()

    if context.json:
        from .common import stdout_json_success

        stdout_json_success(
            rc_path=rc_path, warnings=json_warnings, get=dict(get_key_pairs)
        )
    else:
        for k, v in get_key_pairs:
            print_config_item(k, v)
