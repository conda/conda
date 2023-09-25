# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""Conda command line interface parsers."""
from __future__ import annotations

import argparse
import os
import sys
from argparse import (
    REMAINDER,
    SUPPRESS,
    Action,
    RawDescriptionHelpFormatter,
    _CountAction,
    _HelpAction,
    _StoreTrueAction,
)
from argparse import ArgumentParser as ArgumentParserBase
from importlib import import_module
from logging import getLogger
from os.path import abspath, expanduser, join
from subprocess import Popen
from textwrap import dedent

from .. import __version__
from ..auxlib.compat import isiterable
from ..auxlib.ish import dals
from ..base.constants import (
    COMPATIBLE_SHELLS,
    CONDA_HOMEPAGE_URL,
    DepsModifier,
    UpdateModifier,
)
from ..base.context import context
from ..common.constants import NULL
from ..deprecations import deprecated
from .find_commands import find_commands, find_executable

log = getLogger(__name__)

# duplicated code in the interest of import efficiency
on_win = bool(sys.platform == "win32")
user_rc_path = abspath(expanduser("~/.condarc"))
escaped_user_rc_path = user_rc_path.replace("%", "%%")
escaped_sys_rc_path = abspath(join(sys.prefix, ".condarc")).replace("%", "%%")

#: List of built-in commands; these cannot be overridden by plugin subcommands
BUILTIN_COMMANDS = {
    "clean",
    "compare",
    "config",
    "create",
    "info",
    "init",
    "install",
    "list",
    "package",
    "remove",
    "rename",
    "run",
    "search",
    "update",
    "upgrade",
    "notices",
}


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
        version="conda %s" % __version__,
        help="Show the conda version number and exit.",
    )

    sub_parsers = parser.add_subparsers(
        metavar="COMMAND",
        title="commands",
        description="The following built-in and plugins subcommands are available.",
        dest="cmd",
        action=_GreedySubParsersAction,
    )

    configure_parser_clean(sub_parsers)
    configure_parser_compare(sub_parsers)
    configure_parser_config(sub_parsers)
    configure_parser_create(sub_parsers)
    configure_parser_info(sub_parsers)
    configure_parser_init(sub_parsers)
    configure_parser_install(sub_parsers)
    configure_parser_list(sub_parsers)
    configure_parser_notices(sub_parsers)
    configure_parser_package(sub_parsers)
    configure_parser_remove(sub_parsers, aliases=["uninstall"])
    configure_parser_rename(sub_parsers)
    configure_parser_run(sub_parsers)
    configure_parser_search(sub_parsers)
    configure_parser_update(sub_parsers, aliases=["upgrade"])
    configure_parser_plugins(sub_parsers)

    return parser


def do_call(args: argparse.Namespace, parser: ArgumentParser):
    """
    Serves as the primary entry point for commands referred to in this file and for
    all registered plugin subcommands.
    """
    # let's see if during the parsing phase it was discovered that the
    # called command was in fact a plugin subcommand
    if plugin_subcommand := getattr(args, "_plugin_subcommand", None):
        # pass on the rest of the plugin specific args or fall back to
        # the whole discovered arguments
        context.plugin_manager.invoke_pre_commands(plugin_subcommand.name)
        result = plugin_subcommand.action(getattr(args, "_args", args))
        context.plugin_manager.invoke_post_commands(plugin_subcommand.name)
    elif name := getattr(args, "_executable", None):
        # run the subcommand from executables; legacy path
        deprecated.topic(
            "23.3",
            "24.3",
            topic="Loading conda subcommands via executables",
            addendum="Use the plugin system instead.",
        )
        executable = find_executable(f"conda-{name}")
        if not executable:
            from ..exceptions import CommandNotFoundError

            raise CommandNotFoundError(name)
        return _exec([executable, *args._args], os.environ)
    else:
        # let's call the subcommand the old-fashioned way via the assigned func..
        relative_mod, func_name = args.func.rsplit(".", 1)
        # func_name should always be 'execute'
        module = import_module(relative_mod, "conda.cli")
        command = relative_mod.replace(".main_", "")

        context.plugin_manager.invoke_pre_commands(command)
        result = getattr(module, func_name)(args, parser)
        context.plugin_manager.invoke_post_commands(command)
    return result


def find_builtin_commands(parser):
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


class NullCountAction(_CountAction):
    @staticmethod
    def _ensure_value(namespace, name, value):
        if getattr(namespace, name, NULL) in (NULL, None):
            setattr(namespace, name, value)
        return getattr(namespace, name)

    def __call__(self, parser, namespace, values, option_string=None):
        new_count = self._ensure_value(namespace, self.dest, 0) + 1
        setattr(namespace, self.dest, new_count)


class ExtendConstAction(Action):
    # a derivative of _AppendConstAction and Python 3.8's _ExtendAction
    def __init__(
        self,
        option_strings,
        dest,
        const,
        default=None,
        type=None,
        choices=None,
        required=False,
        help=None,
        metavar=None,
    ):
        super().__init__(
            option_strings=option_strings,
            dest=dest,
            nargs="*",
            const=const,
            default=default,
            type=type,
            choices=choices,
            required=required,
            help=help,
            metavar=metavar,
        )

    def __call__(self, parser, namespace, values, option_string=None):
        items = getattr(namespace, self.dest, None)
        items = [] if items is None else items[:]
        items.extend(values or [self.const])
        setattr(namespace, self.dest, items)


# #############################################################################################
#
# sub-parsers
#
# #############################################################################################


def configure_parser_plugins(sub_parsers) -> None:
    """
    For each of the provided plugin-based subcommands, we'll create
    a new subparser for an improved help printout and calling the
    :meth:`~conda.plugins.types.CondaSubcommand.configure_parser`
    with the newly created subcommand specific argument parser.
    """
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

    # `conda env` subcommand is a first-party conda subcommand even though it uses the legacy
    # subcommand framework, so `conda env` must still be allowed when plugins are disabled
    legacy = (
        ["env"]
        if context.no_plugins
        else set(find_commands()).difference(plugin_subcommands)
    )
    for name in legacy:
        # if the name of the plugin-based subcommand overlaps a built-in
        # subcommand, we print an error
        if name in BUILTIN_COMMANDS:
            log.error(
                dals(
                    f"""
                    The (legacy) plugin '{name}' is trying to override the built-in command
                    with the same name, which is not allowed.

                    Please uninstall the plugin to stop seeing this error message.
                    """
                )
            )
            continue

        parser = sub_parsers.add_parser(
            name,
            description=f"See `conda {name} --help`.",
            help=f"See `conda {name} --help`.",
            add_help=False,  # defer to subcommand's help processing
        )

        # case 3: legacy plugins are always greedy
        parser.greedy = True

        parser.set_defaults(_executable=name)


def configure_parser_clean(sub_parsers):
    descr = "Remove unused packages and caches."
    example = dals(
        """
        Examples::

            conda clean --tarballs
        """
    )
    p = sub_parsers.add_parser(
        "clean",
        description=descr,
        help=descr,
        epilog=example,
    )

    removal_target_options = p.add_argument_group("Removal Targets")
    removal_target_options.add_argument(
        "-a",
        "--all",
        action="store_true",
        help="Remove index cache, lock files, unused cache packages, tarballs, and logfiles.",
    )
    removal_target_options.add_argument(
        "-i",
        "--index-cache",
        action="store_true",
        help="Remove index cache.",
    )
    removal_target_options.add_argument(
        "-p",
        "--packages",
        action="store_true",
        help="Remove unused packages from writable package caches. "
        "WARNING: This does not check for packages installed using "
        "symlinks back to the package cache.",
    )
    removal_target_options.add_argument(
        "-t",
        "--tarballs",
        action="store_true",
        help="Remove cached package tarballs.",
    )
    removal_target_options.add_argument(
        "-f",
        "--force-pkgs-dirs",
        action="store_true",
        help="Remove *all* writable package caches. This option is not included with the --all "
        "flag. WARNING: This will break environments with packages installed using symlinks "
        "back to the package cache.",
    )
    removal_target_options.add_argument(
        "-c",  # for tempfile extension (.c~)
        "--tempfiles",
        const=sys.prefix,
        action=ExtendConstAction,
        help=(
            "Remove temporary files that could not be deleted earlier due to being in-use.  "
            "The argument for the --tempfiles flag is a path (or list of paths) to the "
            "environment(s) where the tempfiles should be found and removed."
        ),
    )
    removal_target_options.add_argument(
        "-l",
        "--logfiles",
        action="store_true",
        help="Remove log files.",
    )

    add_output_and_prompt_options(p)

    p.set_defaults(func=".main_clean.execute")


def configure_parser_info(sub_parsers):
    help = "Display information about current conda install."

    p = sub_parsers.add_parser(
        "info",
        description=help,
        help=help,
    )
    add_parser_json(p)
    p.add_argument(
        "--offline",
        action="store_true",
        default=NULL,
        help=SUPPRESS,
    )
    p.add_argument(
        "-a",
        "--all",
        dest="verbosity",
        action=deprecated.action(
            "24.3",
            "24.9",
            _StoreTrueAction,
            addendum="Use `--verbose` instead.",
        ),
    )
    p.add_argument(
        "--base",
        action="store_true",
        help="Display base environment path.",
    )
    # TODO: deprecate 'conda info --envs' and create 'conda list --envs'
    p.add_argument(
        "-e",
        "--envs",
        action="store_true",
        help="List all known conda environments.",
    )
    p.add_argument(
        "-l",
        "--license",
        action="store_true",
        help=SUPPRESS,
    )
    p.add_argument(
        "-s",
        "--system",
        action="store_true",
        help="List environment variables.",
    )
    p.add_argument(
        "--root",
        action="store_true",
        help=SUPPRESS,
        dest="base",
    )
    p.add_argument(
        "--unsafe-channels",
        action="store_true",
        help="Display list of channels with tokens exposed.",
    )

    p.add_argument(
        "packages",
        action="store",
        nargs="*",
        help=SUPPRESS,
    )

    p.set_defaults(func=".main_info.execute")


def configure_parser_config(sub_parsers):
    help_ = "Modify configuration values in .condarc."
    descr = (
        dedent(
            """
    This is modeled after the git
    config command.  Writes to the user .condarc file (%s) by default. Use the
    --show-sources flag to display all identified configuration locations on
    your computer.

    """
        )
        % escaped_user_rc_path
    )

    # Note, the extra whitespace in the list keys is on purpose. It's so the
    # formatting from help2man is still valid YAML (otherwise it line wraps the
    # keys like "- conda - defaults"). Technically the parser here still won't
    # recognize it because it removes the indentation, but at least it will be
    # valid.
    additional_descr = (
        dedent(
            """
    See `conda config --describe` or %s/docs/config.html
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
        % CONDA_HOMEPAGE_URL
    )

    p = sub_parsers.add_parser(
        "config",
        description=descr,
        help=help_,
        epilog=additional_descr,
    )
    add_parser_json(p)

    # TODO: use argparse.FileType
    config_file_location_group = p.add_argument_group(
        "Config File Location Selection",
        "Without one of these flags, the user config file at '%s' is used."
        % escaped_user_rc_path,
    )
    location = config_file_location_group.add_mutually_exclusive_group()
    location.add_argument(
        "--system",
        action="store_true",
        help="Write to the system .condarc file at '%s'." % escaped_sys_rc_path,
    )
    location.add_argument(
        "--env",
        action="store_true",
        help="Write to the active conda environment .condarc file (%s). "
        "If no environment is active, write to the user config file (%s)."
        ""
        % (
            context.active_prefix or "<no active environment>",
            escaped_user_rc_path,
        ),
    )
    location.add_argument("--file", action="store", help="Write to the given file.")

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
        nargs=1,
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

    p.set_defaults(func=".main_config.execute")


def configure_parser_create(sub_parsers):
    help = "Create a new conda environment from a list of specified packages. "
    descr = (
        help + "To use the newly-created environment, use 'conda activate "
        "envname'. This command requires either the -n NAME or -p PREFIX "
        "option."
    )

    example = dedent(
        """
    Examples:

    Create an environment containing the package 'sqlite'::

        conda create -n myenv sqlite

    Create an environment (env2) as a clone of an existing environment (env1)::

        conda create -n env2 --clone path/to/file/env1

    """
    )
    p = sub_parsers.add_parser(
        "create",
        description=descr,
        help=help,
        epilog=example,
    )
    p.add_argument(
        "--clone",
        action="store",
        help="Create a new environment as a copy of an existing local environment.",
        metavar="ENV",
    )
    solver_mode_options, package_install_options = add_parser_create_install_update(
        p, prefix_required=True
    )
    add_parser_default_packages(solver_mode_options)
    add_parser_solver(solver_mode_options)
    p.add_argument(
        "-m",
        "--mkdir",
        action="store_true",
        help=SUPPRESS,
    )
    p.add_argument(
        "--dev",
        action=NullCountAction,
        help="Use `sys.executable -m conda` in wrapper scripts instead of CONDA_EXE. "
        "This is mainly for use during tests where we test new conda sources "
        "against old Python versions.",
        dest="dev",
        default=NULL,
    )
    p.set_defaults(func=".main_create.execute")


def configure_parser_init(sub_parsers):
    help = "Initialize conda for shell interaction."
    descr = help

    epilog = dals(
        """
        Key parts of conda's functionality require that it interact directly with the shell
        within which conda is being invoked. The `conda activate` and `conda deactivate` commands
        specifically are shell-level commands. That is, they affect the state (e.g. environment
        variables) of the shell context being interacted with. Other core commands, like
        `conda create` and `conda install`, also necessarily interact with the shell environment.
        They're therefore implemented in ways specific to each shell. Each shell must be configured
        to make use of them.

        This command makes changes to your system that are specific and customized for each shell.
        To see the specific files and locations on your system that will be affected before, use
        the '--dry-run' flag.  To see the exact changes that are being or will be made to each
        location, use the '--verbose' flag.

        IMPORTANT: After running `conda init`, most shells will need to be closed and restarted for
        changes to take effect.

        """
    )

    # dev_example = dedent("""
    #     # An example for creating an environment to develop on conda's own code. Clone the
    #     # conda repo and install a dedicated miniconda within it. Remove all remnants of
    #     # conda source files in the `site-packages` directory associated with
    #     # `~/conda/devenv/bin/python`. Write a `conda.pth` file in that `site-packages`
    #     # directory pointing to source code in `~/conda`, the current working directory.
    #     # Write commands to stdout, suitable for bash `eval`, that sets up the current
    #     # shell as a dev environment.
    #
    #         $ CONDA_PROJECT_ROOT="~/conda"
    #         $ git clone git@github.com:conda/conda "$CONDA_PROJECT_ROOT"
    #         $ cd "$CONDA_PROJECT_ROOT"
    #         $ wget https://repo.continuum.io/miniconda/Miniconda3-latest-Linux-x86_64.sh
    #         $ bash Miniconda3-latest-Linux-x86_64.sh -bfp ./devenv
    #         $ eval "$(./devenv/bin/python -m conda init --dev bash)"
    #
    #
    # """)

    p = sub_parsers.add_parser(
        "init",
        description=descr,
        help=help,
        epilog=epilog,
    )

    p.add_argument(
        "--dev",
        action="store_true",
        help=SUPPRESS,
        default=NULL,
    )

    p.add_argument(
        "--all",
        action="store_true",
        help="Initialize all currently available shells.",
        default=NULL,
    )

    setup_type_group = p.add_argument_group("setup type")
    setup_type_group.add_argument(
        "--install",
        action="store_true",
        help=SUPPRESS,
        default=NULL,
    )
    setup_type_group.add_argument(
        "--user",
        action="store_true",
        dest="user",
        help="Initialize conda for the current user (default).",
        default=True,
    )
    setup_type_group.add_argument(
        "--no-user",
        action="store_false",
        dest="user",
        help="Don't initialize conda for the current user.",
    )
    setup_type_group.add_argument(
        "--system",
        action="store_true",
        help="Initialize conda for all users on the system.",
        default=NULL,
    )
    setup_type_group.add_argument(
        "--reverse",
        action="store_true",
        help="Undo effects of last conda init.",
        default=NULL,
    )

    p.add_argument(
        "shells",
        nargs="*",
        choices=COMPATIBLE_SHELLS,
        metavar="SHELLS",
        help=(
            "One or more shells to be initialized. If not given, the default value is 'bash' on "
            "unix and 'cmd.exe' & 'powershell' on Windows. Use the '--all' flag to initialize all "
            f"shells. Available shells: {sorted(COMPATIBLE_SHELLS)}"
        ),
        default=["cmd.exe", "powershell"] if on_win else ["bash"],
    )

    if on_win:
        p.add_argument(
            "--anaconda-prompt",
            action="store_true",
            help="Add an 'Anaconda Prompt' icon to your desktop.",
            default=NULL,
        )

    add_parser_json(p)
    p.add_argument(
        "-d",
        "--dry-run",
        action="store_true",
        help="Only display what would have been done.",
    )
    p.set_defaults(func=".main_init.execute")


def configure_parser_install(sub_parsers):
    help = "Install a list of packages into a specified conda environment."
    descr = dedent(
        help
        + """

    This command accepts a list of package specifications (e.g, bitarray=0.8)
    and installs a set of packages consistent with those specifications and
    compatible with the underlying environment. If full compatibility cannot
    be assured, an error is reported and the environment is not changed.

    Conda attempts to install the newest versions of the requested packages. To
    accomplish this, it may update some packages that are already installed, or
    install additional packages. To prevent existing packages from updating,
    use the --freeze-installed option. This may force conda to install older
    versions of the requested packages, and it does not prevent additional
    dependency packages from being installed.

    If you wish to skip dependency checking altogether, use the '--no-deps'
    option. This may result in an environment with incompatible packages, so
    this option must be used with great caution.

    conda can also be called with a list of explicit conda package filenames
    (e.g. ./lxml-3.2.0-py27_0.tar.bz2). Using conda in this mode implies the
    --no-deps option, and should likewise be used with great caution. Explicit
    filenames and package specifications cannot be mixed in a single command.
    """
    )
    example = dedent(
        """
    Examples:

    Install the package 'scipy' into the currently-active environment::

        conda install scipy

    Install a list of packages into an environment, myenv::

        conda install -n myenv scipy curl wheel

    Install a specific version of 'python' into an environment, myenv::

        conda install -p path/to/myenv python=3.11

    """
    )
    p = sub_parsers.add_parser(
        "install",
        description=descr,
        help=help,
        epilog=example,
    )
    p.add_argument(
        "--revision",
        action="store",
        help="Revert to the specified REVISION.",
        metavar="REVISION",
    )

    solver_mode_options, package_install_options = add_parser_create_install_update(p)

    add_parser_prune(solver_mode_options)
    add_parser_solver(solver_mode_options)
    solver_mode_options.add_argument(
        "--force-reinstall",
        action="store_true",
        default=NULL,
        help="Ensure that any user-requested package for the current operation is uninstalled and "
        "reinstalled, even if that package already exists in the environment.",
    )
    add_parser_update_modifiers(solver_mode_options)
    package_install_options.add_argument(
        "-m",
        "--mkdir",
        action="store_true",
        help="Create the environment directory, if necessary.",
    )
    package_install_options.add_argument(
        "--clobber",
        action="store_true",
        default=NULL,
        help="Allow clobbering (i.e. overwriting) of overlapping file paths "
        "within packages and suppress related warnings.",
    )
    p.add_argument(
        "--dev",
        action=NullCountAction,
        help="Use `sys.executable -m conda` in wrapper scripts instead of CONDA_EXE. "
        "This is mainly for use during tests where we test new conda sources "
        "against old Python versions.",
        dest="dev",
        default=NULL,
    )
    p.set_defaults(func=".main_install.execute")


def configure_parser_list(sub_parsers):
    descr = "List installed packages in a conda environment."

    # Note, the formatting of this is designed to work well with help2man
    examples = dedent(
        """
    Examples:

    List all packages in the current environment::

        conda list

    List all packages in reverse order::

        conda list --reverse

    List all packages installed into the environment 'myenv'::

        conda list -n myenv

    List all packages that begin with the letters "py", using regex::

        conda list ^py

    Save packages for future use::

        conda list --export > package-list.txt

    Reinstall packages from an export file::

        conda create -n myenv --file package-list.txt

    """
    )
    p = sub_parsers.add_parser(
        "list",
        description=descr,
        help=descr,
        formatter_class=RawDescriptionHelpFormatter,
        epilog=examples,
        add_help=False,
    )
    add_parser_help(p)
    add_parser_prefix(p)
    add_parser_json(p)
    add_parser_show_channel_urls(p)
    p.add_argument(
        "--reverse",
        action="store_true",
        default=False,
        help="List installed packages in reverse order.",
    )
    p.add_argument(
        "-c",
        "--canonical",
        action="store_true",
        help="Output canonical names of packages only.",
    )
    p.add_argument(
        "-f",
        "--full-name",
        action="store_true",
        help="Only search for full names, i.e., ^<regex>$. "
        "--full-name NAME is identical to regex '^NAME$'.",
    )
    p.add_argument(
        "--explicit",
        action="store_true",
        help="List explicitly all installed conda packages with URL "
        "(output may be used by conda create --file).",
    )
    p.add_argument(
        "--md5",
        action="store_true",
        help="Add MD5 hashsum when using --explicit.",
    )
    p.add_argument(
        "-e",
        "--export",
        action="store_true",
        help="Output explicit, machine-readable requirement strings instead of "
        "human-readable lists of packages. This output may be used by "
        "conda create --file.",
    )
    p.add_argument(
        "-r",
        "--revisions",
        action="store_true",
        help="List the revision history.",
    )
    p.add_argument(
        "--no-pip",
        action="store_false",
        default=True,
        dest="pip",
        help="Do not include pip-only installed packages.",
    )
    p.add_argument(
        "regex",
        action="store",
        nargs="?",
        help="List only packages matching this regular expression.",
    )
    p.set_defaults(func=".main_list.execute")


def configure_parser_compare(sub_parsers):
    descr = "Compare packages between conda environments."

    # Note, the formatting of this is designed to work well with help2man
    examples = dedent(
        """
    Examples:

    Compare packages in the current environment with respect
    to 'environment.yml' located in the current working directory::

        conda compare environment.yml

    Compare packages installed into the environment 'myenv' with respect
    to 'environment.yml' in a different directory::

        conda compare -n myenv path/to/file/environment.yml

    """
    )
    p = sub_parsers.add_parser(
        "compare",
        description=descr,
        help=descr,
        formatter_class=RawDescriptionHelpFormatter,
        epilog=examples,
        add_help=False,
    )
    add_parser_help(p)
    add_parser_json(p)
    add_parser_prefix(p)
    p.add_argument(
        "file",
        action="store",
        help="Path to the environment file that is to be compared against.",
    )
    p.set_defaults(func=".main_compare.execute")


def configure_parser_package(sub_parsers):
    descr = "Create low-level conda packages. (EXPERIMENTAL)"
    p = sub_parsers.add_parser(
        "package",
        description=descr,
        help=descr,
    )
    add_parser_prefix(p)
    p.add_argument(
        "-w",
        "--which",
        metavar="PATH",
        nargs="+",
        action="store",
        help="Given some file's PATH, print which conda package the file came from.",
    )
    p.add_argument(
        "-r",
        "--reset",
        action="store_true",
        help="Remove all untracked files and exit.",
    )
    p.add_argument(
        "-u",
        "--untracked",
        action="store_true",
        help="Display all untracked files and exit.",
    )
    p.add_argument(
        "--pkg-name",
        action="store",
        default="unknown",
        help="Designate package name of the package being created.",
    )
    p.add_argument(
        "--pkg-version",
        action="store",
        default="0.0",
        help="Designate package version of the package being created.",
    )
    p.add_argument(
        "--pkg-build",
        action="store",
        default=0,
        help="Designate package build number of the package being created.",
    )
    p.set_defaults(func=".main_package.execute")


def configure_parser_remove(sub_parsers, aliases):
    help_ = "Remove a list of packages from a specified conda environment. "
    descr = dals(
        f"""
        {help_}
        "Use `--all` flag to remove all packages and the environment itself."

        This command will also remove any package that depends on any of the
        specified packages as well---unless a replacement can be found without
        that dependency. If you wish to skip this dependency checking and remove
        just the requested packages, add the '--force' option. Note however that
        this may result in a broken environment, so use this with caution.
        """
    )
    example = dals(
        """
        Examples:

        Remove the package 'scipy' from the currently-active environment::

            conda remove scipy

        Remove a list of packages from an environemnt 'myenv'::

            conda remove -n myenv scipy curl wheel

        Remove all packages from environment `myenv` and the environment itself::

            conda remove -n myenv --all

        """
    )
    p = sub_parsers.add_parser(
        "remove",
        formatter_class=RawDescriptionHelpFormatter,
        description=descr,
        help=help_,
        epilog=example,
        add_help=False,
        aliases=aliases,
    )
    add_parser_help(p)
    add_parser_pscheck(p)

    add_parser_prefix(p)
    add_parser_channels(p)

    solver_mode_options = p.add_argument_group("Solver Mode Modifiers")
    solver_mode_options.add_argument(
        "--all",
        action="store_true",
        help="Remove all packages, i.e., the entire environment.",
    )
    solver_mode_options.add_argument(
        "--features",
        action="store_true",
        help="Remove features (instead of packages).",
    )
    solver_mode_options.add_argument(
        "--force-remove",
        "--force",
        action="store_true",
        help="Forces removal of a package without removing packages that depend on it. "
        "Using this option will usually leave your environment in a broken and "
        "inconsistent state.",
        dest="force_remove",
    )
    solver_mode_options.add_argument(
        "--no-pin",
        action="store_true",
        dest="ignore_pinned",
        default=NULL,
        help="Ignore pinned package(s) that apply to the current operation. "
        "These pinned packages might come from a .condarc file or a file in "
        "<TARGET_ENVIRONMENT>/conda-meta/pinned.",
    )
    add_parser_prune(solver_mode_options)
    add_parser_solver(solver_mode_options)

    add_parser_networking(p)
    add_output_and_prompt_options(p)

    p.add_argument(
        "package_names",
        metavar="package_name",
        action="store",
        nargs="*",
        help="Package names to remove from the environment.",
    )
    p.add_argument(
        "--dev",
        action=NullCountAction,
        help="Use `sys.executable -m conda` in wrapper scripts instead of CONDA_EXE. "
        "This is mainly for use during tests where we test new conda sources "
        "against old Python versions.",
        dest="dev",
        default=NULL,
    )

    p.set_defaults(func=".main_remove.execute")


def configure_parser_run(sub_parsers):
    help = "Run an executable in a conda environment."
    descr = help
    example = dedent(
        """

    Example usage::

        $ conda create -y -n my-python-env python=3
        $ conda run -n my-python-env python --version
    """
    )

    p = sub_parsers.add_parser(
        "run",
        description=descr,
        help=help,
        epilog=example,
    )

    add_parser_prefix(p)
    add_parser_verbose(p)

    p.add_argument(
        "--dev",
        action=NullCountAction,
        help="Sets `CONDA_EXE` to `python -m conda`, assuming the current "
        "working directory contains the root of conda development sources. "
        "This is mainly for use during tests where we test new conda sources "
        "against old Python versions.",
        dest="dev",
        default=NULL,
    )

    p.add_argument(
        "--debug-wrapper-scripts",
        action=NullCountAction,
        help="When this is set, where implemented, the shell wrapper scripts"
        "will use the echo command to print debugging information to "
        "stderr (standard error).",
        dest="debug_wrapper_scripts",
        default=NULL,
    )
    p.add_argument(
        "--cwd",
        help="Current working directory for command to run in. Defaults to "
        "the user's current working directory if no directory is specified.",
        default=os.getcwd(),
    )
    p.add_argument(
        "--no-capture-output",
        "--live-stream",
        action="store_true",
        help="Don't capture stdout/stderr (standard out/standard error).",
        default=False,
    )

    p.add_argument(
        "executable_call",
        nargs=REMAINDER,
        help="Executable name, with additional arguments to be passed to the executable "
        "on invocation.",
    )

    p.set_defaults(func=".main_run.execute")


def configure_parser_search(sub_parsers):
    help = "Search for packages and display associated information using the MatchSpec format."
    descr = f"""{help} MatchSpec is a query language for conda packages.
    """

    example = dedent(
        """
    Examples:

    Search for a specific package named 'scikit-learn'::

        conda search scikit-learn

    Search for packages containing 'scikit' in the package name::

        conda search *scikit*

    Note that your shell may expand '*' before handing the command over to conda.
    Therefore, it is sometimes necessary to use single or double quotes around the query::

        conda search '*scikit'
        conda search "*scikit*"

    Search for packages for 64-bit Linux (by default, packages for your current
    platform are shown)::

        conda search numpy[subdir=linux-64]

    Search for a specific version of a package::

        conda search 'numpy>=1.12'

    Search for a package on a specific channel::

        conda search conda-forge::numpy
        conda search 'numpy[channel=conda-forge, subdir=osx-64]'
    """
    )
    p = sub_parsers.add_parser(
        "search",
        description=descr,
        help=help,
        epilog=example,
    )
    p.add_argument(
        "--envs",
        action="store_true",
        help="Search all of the current user's environments. If run as Administrator "
        "(on Windows) or UID 0 (on unix), search all known environments on the system.",
    )
    p.add_argument(
        "-i",
        "--info",
        action="store_true",
        help="Provide detailed information about each package.",
    )
    p.add_argument(
        "--subdir",
        "--platform",
        action="store",
        dest="subdir",
        help="Search the given subdir. Should be formatted like 'osx-64', 'linux-32', "
        "'win-64', and so on. The default is to search the current platform.",
        default=NULL,
    )
    p.add_argument(
        "match_spec",
        default="*",
        nargs="?",
        help=SUPPRESS,
    )

    p.add_argument(
        "--canonical",
        action="store_true",
        help=SUPPRESS,
    )
    p.add_argument(
        "-f",
        "--full-name",
        action="store_true",
        help=SUPPRESS,
    )
    p.add_argument(
        "--names-only",
        action="store_true",
        help=SUPPRESS,
    )
    add_parser_known(p)
    p.add_argument(
        "-o",
        "--outdated",
        action="store_true",
        help=SUPPRESS,
    )
    p.add_argument(
        "--spec",
        action="store_true",
        help=SUPPRESS,
    )
    p.add_argument(
        "--reverse-dependency",
        action="store_true",
        # help="Perform a reverse dependency search. Use 'conda search package --info' "
        #      "to see the dependencies of a package.",
        help=SUPPRESS,  # TODO: re-enable once we have --reverse-dependency working again
    )

    add_parser_channels(p)
    add_parser_networking(p)
    add_parser_json(p)
    p.set_defaults(func=".main_search.execute")


def configure_parser_update(sub_parsers, aliases):
    help_ = "Update conda packages to the latest compatible version."
    descr = dals(
        f"""
        {help_}

        This command accepts a list of package names and updates them to the latest
        versions that are compatible with all other packages in the environment.

        Conda attempts to install the newest versions of the requested packages. To
        accomplish this, it may update some packages that are already installed, or
        install additional packages. To prevent existing packages from updating,
        use the --no-update-deps option. This may force conda to install older
        versions of the requested packages, and it does not prevent additional
        dependency packages from being installed.
        """
    )
    example = dals(
        """
        Examples:

            conda update -n myenv scipy

        """
    )

    p = sub_parsers.add_parser(
        "update",
        description=descr,
        help=help_,
        epilog=example,
        aliases=aliases,
    )
    solver_mode_options, package_install_options = add_parser_create_install_update(p)

    add_parser_prune(solver_mode_options)
    add_parser_solver(solver_mode_options)
    solver_mode_options.add_argument(
        "--force-reinstall",
        action="store_true",
        default=NULL,
        help="Ensure that any user-requested package for the current operation is uninstalled and "
        "reinstalled, even if that package already exists in the environment.",
    )
    add_parser_update_modifiers(solver_mode_options)

    package_install_options.add_argument(
        "--clobber",
        action="store_true",
        default=NULL,
        help="Allow clobbering of overlapping file paths within packages, "
        "and suppress related warnings.",
    )
    p.set_defaults(func=".main_update.execute")


NOTICES_HELP = "Retrieve latest channel notifications."
NOTICES_DESCRIPTION = dals(
    f"""
    {NOTICES_HELP}

    Conda channel maintainers have the option of setting messages that
    users will see intermittently. Some of these notices are informational
    while others are messages concerning the stability of the channel.

    """
)


def configure_parser_notices(sub_parsers, name="notices"):
    example = dals(
        f"""
        Examples::

        conda {name}

        conda {name} -c defaults

        """
    )
    p = sub_parsers.add_parser(
        name,
        description=NOTICES_DESCRIPTION,
        help=NOTICES_HELP,
        epilog=example,
    )
    add_parser_channels(p)
    p.set_defaults(func=".main_notices.execute")


def configure_parser_rename(sub_parsers) -> None:
    help = "Rename an existing environment."
    descr = dals(
        f"""
        {help}

        This command renames a conda environment via its name (-n/--name) or
        its prefix (-p/--prefix).

        The base environment and the currently-active environment cannot be renamed.
        """
    )

    example = dals(
        """
        Examples::

            conda rename -n test123 test321

            conda rename --name test123 test321

            conda rename -p path/to/test123 test321

            conda rename --prefix path/to/test123 test321

        """
    )

    p = sub_parsers.add_parser(
        "rename",
        formatter_class=RawDescriptionHelpFormatter,
        description=descr,
        help=help,
        epilog=example,
    )
    # Add name and prefix args
    add_parser_prefix(p)

    p.add_argument("destination", help="New name for the conda environment.")
    # TODO: deprecate --force in favor of --yes
    p.add_argument(
        "--force",
        help="Force rename of an environment.",
        action="store_true",
        default=False,
    )
    p.add_argument(
        "-d",
        "--dry-run",
        help="Only display what would have been done by the current command, arguments, "
        "and other flags.",
        action="store_true",
        default=False,
    )
    p.set_defaults(func=".main_rename.execute")


# #############################################################################################
#
# parser helpers
#
# #############################################################################################


def add_parser_create_install_update(p, prefix_required=False):
    add_parser_prefix(p, prefix_required)
    add_parser_channels(p)
    solver_mode_options = add_parser_solver_mode(p)
    package_install_options = add_parser_package_install_options(p)
    add_parser_networking(p)

    output_and_prompt_options = add_output_and_prompt_options(p)
    output_and_prompt_options.add_argument(
        "--download-only",
        action="store_true",
        default=NULL,
        help="Solve an environment and ensure package caches are populated, but exit "
        "prior to unlinking and linking packages into the prefix.",
    )
    add_parser_show_channel_urls(output_and_prompt_options)

    add_parser_pscheck(p)
    add_parser_known(p)

    # Add the file kwarg. We don't use {action="store", nargs='*'} as we don't
    # want to gobble up all arguments after --file.
    p.add_argument(
        "--file",
        default=[],
        action="append",
        help="Read package versions from the given file. Repeated file "
        "specifications can be passed (e.g. --file=file1 --file=file2).",
    )
    p.add_argument(
        "packages",
        metavar="package_spec",
        action="store",
        nargs="*",
        help="List of packages to install or update in the conda environment.",
    )

    return solver_mode_options, package_install_options


def add_parser_pscheck(p):
    p.add_argument("--force-pscheck", action="store_true", help=SUPPRESS)


def add_parser_show_channel_urls(p):
    p.add_argument(
        "--show-channel-urls",
        action="store_true",
        dest="show_channel_urls",
        default=NULL,
        help="Show channel urls. "
        "Overrides the value given by `conda config --show show_channel_urls`.",
    )
    p.add_argument(
        "--no-show-channel-urls",
        action="store_false",
        dest="show_channel_urls",
        help=SUPPRESS,
    )


def add_parser_help(p):
    """
    So we can use consistent capitalization and periods in the help. You must
    use the add_help=False argument to ArgumentParser or add_parser to use
    this. Add this first to be consistent with the default argparse output.

    """
    p.add_argument(
        "-h",
        "--help",
        action=_HelpAction,
        help="Show this help message and exit.",
    )


def add_parser_prefix(p, prefix_required=False):
    target_environment_group = p.add_argument_group("Target Environment Specification")
    npgroup = target_environment_group.add_mutually_exclusive_group(
        required=prefix_required
    )
    npgroup.add_argument(
        "-n",
        "--name",
        action="store",
        help="Name of environment.",
        metavar="ENVIRONMENT",
    )
    npgroup.add_argument(
        "-p",
        "--prefix",
        action="store",
        help="Full path to environment location (i.e. prefix).",
        metavar="PATH",
    )


def add_parser_json(p):
    output_and_prompt_options = p.add_argument_group(
        "Output, Prompt, and Flow Control Options"
    )
    output_and_prompt_options.add_argument(
        "--json",
        action="store_true",
        default=NULL,
        help="Report all output as json. Suitable for using conda programmatically.",
    )
    add_parser_verbose(output_and_prompt_options)
    output_and_prompt_options.add_argument(
        "-q",
        "--quiet",
        action="store_true",
        default=NULL,
        help="Do not display progress bar.",
    )
    return output_and_prompt_options


def add_output_and_prompt_options(p):
    output_and_prompt_options = add_parser_json(p)
    output_and_prompt_options.add_argument(
        "-d",
        "--dry-run",
        action="store_true",
        help="Only display what would have been done.",
    )
    output_and_prompt_options.add_argument(
        "-y",
        "--yes",
        action="store_true",
        default=NULL,
        help="Sets any confirmation values to 'yes' automatically. "
        "Users will not be asked to confirm any adding, deleting, backups, etc.",
    )
    return output_and_prompt_options


def add_parser_channels(p):
    channel_customization_options = p.add_argument_group("Channel Customization")
    channel_customization_options.add_argument(
        "-c",
        "--channel",
        dest="channel",  # apparently conda-build uses this; someday rename to channels are remove context.channels alias to channel  # NOQA
        # TODO: if you ever change 'channel' to 'channels', make sure you modify the context.channels property accordingly # NOQA
        action="append",
        help=(
            "Additional channel to search for packages. These are URLs searched in the order "
            "they are given (including local directories using the 'file://' syntax or "
            "simply a path like '/home/conda/mychan' or '../mychan'). Then, the defaults "
            "or channels from .condarc are searched (unless --override-channels is given). "
            "You can use 'defaults' to get the default packages for conda. You can also "
            "use any name and the .condarc channel_alias value will be prepended. The "
            "default channel_alias is https://conda.anaconda.org/."
        ),
    )
    channel_customization_options.add_argument(
        "--use-local",
        action="store_true",
        default=NULL,
        help="Use locally built packages. Identical to '-c local'.",
    )
    channel_customization_options.add_argument(
        "--override-channels",
        action="store_true",
        help="""Do not search default or .condarc channels.  Requires --channel.""",
    )
    channel_customization_options.add_argument(
        "--repodata-fn",
        action="append",
        dest="repodata_fns",
        help=(
            "Specify file name of repodata on the remote server where your channels "
            "are configured or within local backups. Conda will try whatever you "
            "specify, but will ultimately fall back to repodata.json if your specs are "
            "not satisfiable with what you specify here. This is used to employ repodata "
            "that is smaller and reduced in time scope. You may pass this flag more than "
            "once. Leftmost entries are tried first, and the fallback to repodata.json "
            "is added for you automatically. For more information, see "
            "conda config --describe repodata_fns."
        ),
    )
    channel_customization_options.add_argument(
        "--experimental",
        action="append",
        choices=["jlap", "lock"],
        help="jlap: Download incremental package index data from repodata.jlap; implies 'lock'. "
        "lock: use locking when reading, updating index (repodata.json) cache. Now enabled.",
    )
    channel_customization_options.add_argument(
        "--no-lock",
        action="store_true",
        help="Disable locking when reading, updating index (repodata.json) cache. ",
    )
    return channel_customization_options


def add_parser_solver_mode(p):
    solver_mode_options = p.add_argument_group("Solver Mode Modifiers")
    deps_modifiers = solver_mode_options.add_mutually_exclusive_group()
    solver_mode_options.add_argument(
        "--strict-channel-priority",
        action="store_const",
        dest="channel_priority",
        default=NULL,
        const="strict",
        help="Packages in lower priority channels are not considered if a package "
        "with the same name appears in a higher priority channel.",
    )
    solver_mode_options.add_argument(
        "--channel-priority",
        action="store_true",
        dest="channel_priority",
        default=NULL,
        help=SUPPRESS,
    )
    solver_mode_options.add_argument(
        "--no-channel-priority",
        action="store_const",
        dest="channel_priority",
        default=NULL,
        const="disabled",
        help="Package version takes precedence over channel priority. "
        "Overrides the value given by `conda config --show channel_priority`.",
    )
    deps_modifiers.add_argument(
        "--no-deps",
        action="store_const",
        const=DepsModifier.NO_DEPS,
        dest="deps_modifier",
        help="Do not install, update, remove, or change dependencies. This WILL lead "
        "to broken environments and inconsistent behavior. Use at your own risk.",
        default=NULL,
    )
    deps_modifiers.add_argument(
        "--only-deps",
        action="store_const",
        const=DepsModifier.ONLY_DEPS,
        dest="deps_modifier",
        help="Only install dependencies.",
        default=NULL,
    )
    solver_mode_options.add_argument(
        "--no-pin",
        action="store_true",
        dest="ignore_pinned",
        default=NULL,
        help="Ignore pinned file.",
    )
    return solver_mode_options


def add_parser_update_modifiers(solver_mode_options):
    update_modifiers = solver_mode_options.add_mutually_exclusive_group()
    update_modifiers.add_argument(
        "--freeze-installed",
        "--no-update-deps",
        action="store_const",
        const=UpdateModifier.FREEZE_INSTALLED,
        dest="update_modifier",
        default=NULL,
        help="Do not update or change already-installed dependencies.",
    )
    update_modifiers.add_argument(
        "--update-deps",
        action="store_const",
        const=UpdateModifier.UPDATE_DEPS,
        dest="update_modifier",
        default=NULL,
        help="Update dependencies that have available updates.",
    )
    update_modifiers.add_argument(
        "-S",
        "--satisfied-skip-solve",
        action="store_const",
        const=UpdateModifier.SPECS_SATISFIED_SKIP_SOLVE,
        dest="update_modifier",
        default=NULL,
        help="Exit early and do not run the solver if the requested specs are satisfied. "
        "Also skips aggressive updates as configured by the "
        "'aggressive_update_packages' config setting. Use "
        "'conda info --describe aggressive_update_packages' to view your setting. "
        "--satisfied-skip-solve is similar to the default behavior of 'pip install'.",
    )
    update_modifiers.add_argument(
        "--update-all",
        "--all",
        action="store_const",
        const=UpdateModifier.UPDATE_ALL,
        dest="update_modifier",
        help="Update all installed packages in the environment.",
        default=NULL,
    )
    update_modifiers.add_argument(
        "--update-specs",
        action="store_const",
        const=UpdateModifier.UPDATE_SPECS,
        dest="update_modifier",
        help="Update based on provided specifications.",
        default=NULL,
    )


def add_parser_prune(p):
    p.add_argument(
        "--prune",
        action="store_true",
        default=NULL,
        help=SUPPRESS,
    )


def add_parser_solver(p):
    """
    Add a command-line flag for alternative solver backends.

    See ``context.solver`` for more info.
    """
    group = p.add_mutually_exclusive_group()
    group.add_argument(
        "--solver",
        dest="solver",
        choices=context.plugin_manager.get_solvers(),
        help="Choose which solver backend to use.",
        default=NULL,
    )


def add_parser_networking(p):
    networking_options = p.add_argument_group("Networking Options")
    networking_options.add_argument(
        "-C",
        "--use-index-cache",
        action="store_true",
        default=False,
        help="Use cache of channel index files, even if it has expired. This is useful "
        "if you don't want conda to check whether a new version of the repodata "
        "file exists, which will save bandwidth.",
    )
    networking_options.add_argument(
        "-k",
        "--insecure",
        action="store_false",
        dest="ssl_verify",
        default=NULL,
        help='Allow conda to perform "insecure" SSL connections and transfers. '
        "Equivalent to setting 'ssl_verify' to 'false'.",
    )
    networking_options.add_argument(
        "--offline",
        action="store_true",
        default=NULL,
        help="Offline mode. Don't connect to the Internet.",
    )
    return networking_options


def add_parser_package_install_options(p):
    package_install_options = p.add_argument_group(
        "Package Linking and Install-time Options"
    )
    package_install_options.add_argument(
        "-f",
        "--force",
        action="store_true",
        default=NULL,
        help=SUPPRESS,
    )
    package_install_options.add_argument(
        "--copy",
        action="store_true",
        default=NULL,
        help="Install all packages using copies instead of hard- or soft-linking.",
    )
    if on_win:
        package_install_options.add_argument(
            "--shortcuts",
            action="store_true",
            help=SUPPRESS,
            dest="shortcuts",
            default=NULL,
        )
        package_install_options.add_argument(
            "--no-shortcuts",
            action="store_false",
            help="Don't install start menu shortcuts",
            dest="shortcuts",
            default=NULL,
        )
    return package_install_options


def add_parser_known(p):
    p.add_argument(
        "--unknown",
        action="store_true",
        default=False,
        dest="unknown",
        help=SUPPRESS,
    )


def add_parser_default_packages(p):
    p.add_argument(
        "--no-default-packages",
        action="store_true",
        help="Ignore create_default_packages in the .condarc file.",
    )


def add_parser_verbose(parser):
    parser.add_argument(
        "-v",
        "--verbose",
        action=NullCountAction,
        help=(
            "Can be used multiple times. Once for detailed output, twice for INFO logging, "
            "thrice for DEBUG logging, four times for TRACE logging."
        ),
        dest="verbosity",
        default=NULL,
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help=SUPPRESS,
        default=NULL,
    )
    parser.add_argument(
        "--trace",
        action="store_true",
        help=SUPPRESS,
        default=NULL,
    )
