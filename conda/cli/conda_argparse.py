# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""Conda command line interface parsers."""

from __future__ import annotations

import argparse
import os
import sys
from argparse import (
    SUPPRESS,
    RawDescriptionHelpFormatter,
)
from argparse import ArgumentParser as ArgumentParserBase
from importlib import import_module
from logging import getLogger
from subprocess import Popen

from .. import __version__
from ..common.compat import isiterable, on_win
from ..common.constants import NULL
from .actions import ExtendConstAction, NullCountAction  # noqa: F401
from .helpers import (  # noqa: F401
    add_output_and_prompt_options,
    add_parser_channels,
    add_parser_create_install_update,
    add_parser_default_packages,
    add_parser_help,
    add_parser_json,
    add_parser_known,
    add_parser_networking,
    add_parser_package_install_options,
    add_parser_platform,
    add_parser_prefix,
    add_parser_prefix_to_group,
    add_parser_prune,
    add_parser_pscheck,
    add_parser_show_channel_urls,
    add_parser_solver,
    add_parser_solver_mode,
    add_parser_update_modifiers,
    add_parser_verbose,
)

log = getLogger(__name__)


_DEPRECATED_CONFIGURE_PARSER_EXPORTS: dict[str, str] = {
    "configure_parser_activate": "conda.cli.main_mock_activate",
    "configure_parser_clean": "conda.cli.main_clean",
    "configure_parser_commands": "conda.cli.main_commands",
    "configure_parser_compare": "conda.cli.main_compare",
    "configure_parser_config": "conda.cli.main_config",
    "configure_parser_create": "conda.cli.main_create",
    "configure_parser_deactivate": "conda.cli.main_mock_deactivate",
    "configure_parser_env": "conda.cli.main_env",
    "configure_parser_export": "conda.cli.main_export",
    "configure_parser_info": "conda.cli.main_info",
    "configure_parser_init": "conda.cli.main_init",
    "configure_parser_install": "conda.cli.main_install",
    "configure_parser_list": "conda.cli.main_list",
    "configure_parser_notices": "conda.cli.main_notices",
    "configure_parser_package": "conda.cli.main_package",
    "configure_parser_remove": "conda.cli.main_remove",
    "configure_parser_rename": "conda.cli.main_rename",
    "configure_parser_run": "conda.cli.main_run",
    "configure_parser_search": "conda.cli.main_search",
    "configure_parser_update": "conda.cli.main_update",
}

_DEPRECATED_RC_PATH_EXPORTS = frozenset(
    {
        "user_rc_path",
        "sys_rc_path",
        "escaped_user_rc_path",
        "escaped_sys_rc_path",
    }
)


def __getattr__(name: str):
    # Lazily register deprecated re-exports using conda's deprecation system.
    # deprecated.constant() installs a _ConstantDeprecationRegistry as the module's
    # __getattr__; on first access here we register + return the value silently,
    # and all subsequent accesses go through the registry and emit the warning.
    from ..deprecations import deprecated

    if name in _DEPRECATED_CONFIGURE_PARSER_EXPORTS:
        module_path = _DEPRECATED_CONFIGURE_PARSER_EXPORTS[name]
        mod = import_module(module_path)
        val = mod.configure_parser
        deprecated.constant(
            "26.5",
            "27.3",
            name,
            val,
            addendum=f"Use `from {module_path} import configure_parser` instead.",
        )
        return val

    if name in _DEPRECATED_RC_PATH_EXPORTS:
        from ..base.context import sys_rc_path, user_rc_path

        _rc_addenda = {
            "user_rc_path": "Use `from conda.base.context import user_rc_path` instead.",
            "sys_rc_path": "Use `from conda.base.context import sys_rc_path` instead.",
            "escaped_user_rc_path": "Use `from conda.base.context import user_rc_path` and escape locally.",
            "escaped_sys_rc_path": "Use `from conda.base.context import sys_rc_path` and escape locally.",
        }
        _rc_values = {
            "user_rc_path": user_rc_path,
            "sys_rc_path": sys_rc_path,
            "escaped_user_rc_path": user_rc_path.replace("%", "%%"),
            "escaped_sys_rc_path": sys_rc_path.replace("%", "%%"),
        }
        val = _rc_values[name]
        deprecated.constant(
            "26.5",
            "27.3",
            name,
            val,
            addendum=_rc_addenda[name],
        )
        return val

    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


_BUILTIN_SUBCOMMANDS: list[tuple[str, str, str, dict]] = [
    # (name, module_path, help_text, extra_kwargs)
    ("activate", "conda.cli.main_mock_activate", "Activate a conda environment.", {}),
    ("clean", "conda.cli.main_clean", "Remove unused packages and caches.", {}),
    (
        "commands",
        "conda.cli.main_commands",
        "List all available conda subcommands (including those from plugins). "
        "Generally only used by tab-completion.",
        {},
    ),
    (
        "compare",
        "conda.cli.main_compare",
        "Compare packages between conda environments.",
        {},
    ),
    ("config", "conda.cli.main_config", "Modify configuration values in .condarc.", {}),
    (
        "create",
        "conda.cli.main_create",
        "Create a new conda environment from a list of specified packages.",
        {},
    ),
    (
        "deactivate",
        "conda.cli.main_mock_deactivate",
        "Deactivate the current active conda environment.",
        {},
    ),
    ("env", "conda.cli.main_env", "Create and manage conda environments.", {}),
    ("export", "conda.cli.main_export", "Export a given environment", {}),
    (
        "info",
        "conda.cli.main_info",
        "Display information about current conda install.",
        {},
    ),
    ("init", "conda.cli.main_init", "Initialize conda for shell interaction.", {}),
    (
        "install",
        "conda.cli.main_install",
        "Install a list of packages into a specified conda environment.",
        {},
    ),
    (
        "list",
        "conda.cli.main_list",
        "List installed packages in a conda environment.",
        {},
    ),
    ("notices", "conda.cli.main_notices", "Retrieve latest channel notifications.", {}),
    (
        "package",
        "conda.cli.main_package",
        "Create low-level conda packages. (EXPERIMENTAL)",
        {},
    ),
    (
        "remove",
        "conda.cli.main_remove",
        "Remove a list of packages from a specified conda environment.",
        {"aliases": ["uninstall"]},
    ),
    ("rename", "conda.cli.main_rename", "Rename an existing environment.", {}),
    ("run", "conda.cli.main_run", "Run an executable in a conda environment.", {}),
    (
        "search",
        "conda.cli.main_search",
        "Search for packages and display associated information "
        "using the MatchSpec format.",
        {},
    ),
    (
        "update",
        "conda.cli.main_update",
        "Update conda packages to the latest compatible version.",
        {"aliases": ["upgrade"]},
    ),
]

BUILTIN_COMMANDS = {name for name, *_ in _BUILTIN_SUBCOMMANDS}
for _name, _module, _help, _kw in _BUILTIN_SUBCOMMANDS:
    for _alias in _kw.get("aliases", ()):
        BUILTIN_COMMANDS.add(_alias)
"""Names (and aliases) of built-in commands; these cannot be overridden by plugin subcommands."""


def generate_pre_parser(**kwargs) -> ArgumentParser:
    pre_parser = ArgumentParser(
        description="conda is a tool for managing and deploying applications,"
        " environments and packages.",
        **kwargs,
    )

    add_parser_verbose(pre_parser)
    pre_parser.add_argument(
        "--json",
        action="store_true",
        default=NULL,
        help=SUPPRESS,
    )
    pre_parser.add_argument(
        "--no-plugins",
        action="store_true",
        default=NULL,
        help="Disable all plugins that are not built into conda.",
    )

    return pre_parser


def generate_parser(**kwargs) -> ArgumentParser:
    parser = generate_pre_parser(**kwargs)

    parser.add_argument(
        "-V",
        "--version",
        action="version",
        version=f"conda {__version__}",
        help="Show the conda version number and exit.",
    )

    sub_parsers = parser.add_subparsers(
        metavar="COMMAND",
        title="commands",
        description="The following built-in and plugins subcommands are available.",
        dest="cmd",
        action=_LazySubParsersAction,
        required=True,
    )

    for name, module_path, help_text, extra_kwargs in _BUILTIN_SUBCOMMANDS:
        sub_parsers.add_lazy_subcommand(name, module_path, help_text, **extra_kwargs)

    return parser


def do_call(args: argparse.Namespace, parser: ArgumentParser):
    """
    Serves as the primary entry point for commands referred to in this file and for
    all registered plugin subcommands.
    """
    from ..base.context import context

    # let's see if during the parsing phase it was discovered that the
    # called command was in fact a plugin subcommand
    if plugin_subcommand := getattr(args, "_plugin_subcommand", None):
        # pass on the rest of the plugin specific args or fall back to
        # the whole discovered arguments
        context.plugin_manager.invoke_pre_commands(plugin_subcommand.name)
        result = plugin_subcommand.action(getattr(args, "_args", args))
        context.plugin_manager.invoke_post_commands(plugin_subcommand.name)
    else:
        # let's call the subcommand the old-fashioned way via the assigned func..
        module_name, func_name = args.func.rsplit(".", 1)
        # func_name should always be 'execute'
        module = import_module(module_name)
        command = module_name.split(".")[-1].replace("main_", "")

        context.plugin_manager.invoke_pre_commands(command)
        result = getattr(module, func_name)(args, parser)
        context.plugin_manager.invoke_post_commands(command)
    return result


def find_builtin_commands(parser: ArgumentParserBase) -> tuple[str, ...]:
    # ArgumentParser doesn't have an API for getting back what subparsers
    # exist, so we need to use internal properties to do so.
    return tuple(parser._subparsers._group_actions[0].choices.keys())


class ArgumentParser(ArgumentParserBase):
    def __init__(self, *args, add_help=True, **kwargs):
        kwargs.setdefault("formatter_class", RawDescriptionHelpFormatter)
        super().__init__(*args, add_help=False, **kwargs)

        if add_help:
            add_parser_help(self)

    def _check_value(self, action, value):
        if isinstance(action, _LazySubParsersAction) and isinstance(
            action.choices, dict
        ):
            # Unknown command: discover plugins before rejecting so that plugin
            # subcommands appear in the "choose from" error message.  Must read
            # from _name_parser_map (not choices) after loading because the
            # sort-reassignment above disconnects choices from _name_parser_map.
            if not isiterable(value) and value not in action._name_parser_map:
                action._ensure_plugins_loaded()
            action.choices = dict(sorted(action._name_parser_map.items()))
        elif isinstance(action, _GreedySubParsersAction) and isinstance(
            action.choices, dict
        ):
            action.choices = dict(sorted(action.choices.items()))
        # extend to properly handle when we accept multiple choices and the default is a list
        if action.choices is not None and isiterable(value):
            for element in value:
                super()._check_value(action, element)
        else:
            super()._check_value(action, value)

    def parse_args(self, *args, override_args=None, **kwargs):
        parsed_args = super().parse_args(*args, **kwargs)
        for name, value in (override_args or {}).items():
            if value is not NULL and getattr(parsed_args, name, NULL) is NULL:
                setattr(parsed_args, name, value)
        return parsed_args


class _GreedySubParsersAction(argparse._SubParsersAction):
    """A custom subparser action to conditionally act as a greedy consumer.

    This is a workaround since argparse.REMAINDER does not work as expected,
    see https://github.com/python/cpython/issues/61252.
    """

    def __call__(self, parser, namespace, values, option_string=None):
        super().__call__(parser, namespace, values, option_string)

        parser = self._name_parser_map[values[0]]

        # if the parser has a greedy=True attribute we want to consume all arguments
        # i.e. all unknown args should be passed to the subcommand as is
        if getattr(parser, "greedy", False):
            try:
                unknown = getattr(namespace, argparse._UNRECOGNIZED_ARGS_ATTR)
                delattr(namespace, argparse._UNRECOGNIZED_ARGS_ATTR)
            except AttributeError:
                unknown = ()

            # underscore prefixed indicating this is not a normal argparse argument
            namespace._args = tuple(unknown)

    def _get_subactions(self):
        """Sort actions for subcommands to appear alphabetically in help blurb."""
        return sorted(self._choices_actions, key=lambda action: action.dest)


class _LazyParserMap(dict):
    """A dict that triggers lazy parser loading on key access.

    Used as the _name_parser_map for _LazySubParsersAction so that any
    consumer reading a specific subcommand parser (e.g. sphinx-argparse
    navigating a :path: directive) gets the fully-configured parser rather
    than the lightweight stub registered at generate_parser() time.
    """

    def __init__(self, action):
        super().__init__()
        self._action = action

    @property
    def _ready(self):
        """True once the owning action is initialized and not mid-build."""
        action = self._action
        return hasattr(action, "_lazy_loaders") and not getattr(
            action, "_building", False
        )

    def _resolve(self, key):
        """Ensure *key* is fully loaded (builtin or plugin)."""
        if not self._ready:
            return
        self._action._ensure_loaded(key)
        if not super().__contains__(key):
            self._action._ensure_plugins_loaded()

    def _resolve_all(self):
        """Load every lazy subcommand and all plugins."""
        if not self._ready:
            return
        for name in list(self._action._lazy_loaders):
            self._action._ensure_loaded(name)
        self._action._ensure_plugins_loaded()

    def __getitem__(self, key):
        self._resolve(key)
        return super().__getitem__(key)

    def get(self, key, default=None):
        self._resolve(key)
        return super().get(key, default)

    def __contains__(self, key):
        self._resolve(key)
        return super().__contains__(key)

    def items(self):
        self._resolve_all()
        return super().items()

    def values(self):
        self._resolve_all()
        return super().values()

    def keys(self):
        self._resolve_all()
        return super().keys()

    def __iter__(self):
        self._resolve_all()
        return super().__iter__()

    def __len__(self):
        self._resolve_all()
        return super().__len__()


class _LazySubParsersAction(_GreedySubParsersAction):
    """Extends _GreedySubParsersAction with lazy loading of subcommand parsers.

    Registers lightweight stub parsers for all built-in subcommands at
    generate_parser() time (name + help text only). The real configure_parser
    is called on demand when a subcommand is actually invoked.

    Plugin subcommand discovery is deferred until a non-builtin command is
    requested or --help is displayed.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._name_parser_map = _LazyParserMap(self)
        self.choices = self._name_parser_map
        self._lazy_loaders: dict[str, tuple[str, dict]] = {}
        self._lazy_aliases: dict[str, str] = {}
        self._loading_name: str | None = None
        self._plugins_loaded = False
        self._building = False

    def add_lazy_subcommand(self, name, module_path, help_text, **kwargs):
        """Register a lazy-loaded subcommand with a stub parser."""
        aliases = kwargs.get("aliases", ())
        self._building = True
        try:
            stub = super().add_parser(name, help=help_text, **kwargs)
        finally:
            self._building = False
        self._lazy_loaders[name] = (module_path, kwargs)
        for alias in aliases:
            self._lazy_aliases[alias] = name
        return stub

    def add_parser(self, name, **kwargs):
        """During lazy loading, return the existing stub instead of creating a new parser."""
        if self._loading_name is not None and name in self._name_parser_map:
            parser = self._name_parser_map[name]
            for attr in ("description", "epilog"):
                if attr in kwargs:
                    setattr(parser, attr, kwargs[attr])
            return parser
        return super().add_parser(name, **kwargs)

    def _ensure_loaded(self, name):
        """Load a lazy subcommand's full parser configuration."""
        canonical = self._lazy_aliases.get(name, name)
        if canonical not in self._lazy_loaders:
            return
        module_path, loader_kwargs = self._lazy_loaders.pop(canonical)
        for alias in loader_kwargs.get("aliases", ()):
            self._lazy_aliases.pop(alias, None)
        self._loading_name = canonical
        try:
            mod = import_module(module_path)
            mod.configure_parser(self, **loader_kwargs)
        finally:
            self._loading_name = None

    def _ensure_plugins_loaded(self):
        """Discover and register plugin subcommands on demand."""
        if self._plugins_loaded:
            return
        self._plugins_loaded = True
        configure_parser_plugins(self)

    def __call__(self, parser, namespace, values, option_string=None):
        parser_name = values[0]
        self._ensure_loaded(parser_name)
        # Always discover plugins when a subcommand is dispatched so that
        # the builtin-override check in configure_parser_plugins() runs even
        # when the invoked command is a builtin (e.g. `conda info --help`).
        self._ensure_plugins_loaded()
        super().__call__(parser, namespace, values, option_string)

    def _get_subactions(self):
        """Ensure plugins are discovered before listing subcommands in help."""
        self._ensure_plugins_loaded()
        return super()._get_subactions()


def _exec(executable_args, env_vars):
    return (_exec_win if on_win else _exec_unix)(executable_args, env_vars)


def _exec_win(executable_args, env_vars):
    p = Popen(executable_args, env=env_vars)
    try:
        p.communicate()
    except KeyboardInterrupt:
        p.wait()
    finally:
        sys.exit(p.returncode)


def _exec_unix(executable_args, env_vars):
    os.execvpe(executable_args[0], executable_args, env_vars)


def configure_parser_plugins(sub_parsers) -> None:
    """
    For each of the provided plugin-based subcommands, we'll create
    a new subparser for an improved help printout and calling the
    :meth:`~conda.plugins.types.CondaSubcommand.configure_parser`
    with the newly created subcommand specific argument parser.
    """
    from ..auxlib.ish import dals
    from ..base.context import context

    plugin_subcommands = context.plugin_manager.get_subcommands()
    for name, plugin_subcommand in plugin_subcommands.items():
        # if the name of the plugin-based subcommand overlaps a built-in
        # subcommand, we print an error
        if name in BUILTIN_COMMANDS:
            log.error(
                dals(
                    f"""
                    The plugin '{name}' is trying to override the built-in command
                    with the same name, which is not allowed.

                    Please uninstall the plugin to stop seeing this error message.
                    """
                )
            )
            continue

        parser = sub_parsers.add_parser(
            name,
            description=plugin_subcommand.summary,
            help=plugin_subcommand.summary,
            add_help=False,  # defer to subcommand's help processing
        )

        # case 1: plugin extends the parser
        if plugin_subcommand.configure_parser:
            plugin_subcommand.configure_parser(parser)

            # attempt to add standard help processing, will fail if plugin defines their own
            try:
                add_parser_help(parser)
            except argparse.ArgumentError:
                pass

        # case 2: plugin has their own parser, see _GreedySubParsersAction
        else:
            parser.greedy = True

        # underscore prefixed indicating this is not a normal argparse argument
        parser.set_defaults(_plugin_subcommand=plugin_subcommand)
