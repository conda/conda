# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""
Main entry points for conda-ng
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import argparse

    from conda.cli.conda_argparse import ArgumentParser


def do_call(args: argparse.Namespace, parser: ArgumentParser):
    """
    Serves as the primary entry point for commands referred to in this file and for
    all registered plugin subcommands.

    Patched to import from `conda.ng.cli` instead of `conda.cli`
    """
    from conda.base.context import context

    # let's see if during the parsing phase it was discovered that the
    # called command was in fact a plugin subcommand
    if plugin_subcommand := getattr(args, "_plugin_subcommand", None):
        # pass on the rest of the plugin specific args or fall back to
        # the whole discovered arguments
        context.plugin_manager.invoke_pre_commands(plugin_subcommand.name)
        result = plugin_subcommand.action(getattr(args, "_args", args))
        context.plugin_manager.invoke_post_commands(plugin_subcommand.name)
    elif name := getattr(args, "_executable", None):
        import os
        from shutil import which as find_executable

        from conda.cli.conda_argparse import _exec
        from conda.deprecations import deprecated

        # run the subcommand from executables; legacy path
        deprecated.topic(
            "23.3",
            "26.3",
            topic="Loading conda subcommands via executables",
            addendum="Use the plugin system instead.",
        )
        executable = find_executable(f"conda-{name}")
        if not executable:
            from conda.exceptions import CommandNotFoundError

            raise CommandNotFoundError(name)
        return _exec([executable, *args._args], os.environ)
    else:
        from importlib import import_module

        # let's call the subcommand the old-fashioned way via the assigned func..
        module_name, func_name = args.func.rsplit(".", 1)
        # func_name should always be 'execute'
        module_name_components = module_name.split(".")
        if "conda" in module_name_components:
            conda_idx = module_name_components.index("conda") + 1
            module_name = ".".join(
                [
                    *module_name_components[:conda_idx],
                    "ng",
                    *module_name_components[conda_idx:],
                ]
            )
        module = import_module(module_name)
        command = module_name.split(".")[-1].replace("main_", "")

        context.plugin_manager.invoke_pre_commands(command)
        result = getattr(module, func_name)(args, parser)
        context.plugin_manager.invoke_post_commands(command)
    return result


def main_inner(*args, post_parse_hook=None, **kwargs):
    """Entrypoint for the invocation of CLI interface. E.g. `conda create`."""
    # defer import here so it doesn't hit the 'conda shell.*' subcommands paths
    from conda.base.context import context
    from conda.cli.conda_argparse import generate_parser, generate_pre_parser

    args = args or ["--help"]

    pre_parser = generate_pre_parser(add_help=False)
    args_subset = args[: args.index("--")] if "--" in args else args
    pre_args, _ = pre_parser.parse_known_args(args_subset)

    # the arguments that we want to pass to the main parser later on
    override_args = {
        "json": pre_args.json,
        "debug": pre_args.debug,
        "trace": pre_args.trace,
        "verbosity": pre_args.verbosity,
    }

    context.__init__(argparse_args=pre_args)
    if context.no_plugins:
        context.plugin_manager.disable_external_plugins()

    # reinitialize in case any of the entrypoints modified the context
    context.__init__(argparse_args=pre_args)

    parser = generate_parser(add_help=True)
    args = parser.parse_args(args, override_args=override_args, namespace=pre_args)

    context.__init__(argparse_args=args)

    # TODO:
    # init_loggers()

    # used with main_pip.py
    if post_parse_hook:
        post_parse_hook(args, parser)

    exit_code = do_call(args, parser)
    if isinstance(exit_code, int):
        return exit_code
    elif hasattr(exit_code, "rc"):
        return exit_code.rc


def main(*args, **kwargs):
    import sys

    # conda.common.compat contains only stdlib imports
    from conda.common.compat import ensure_text_type
    from conda.exception_handler import conda_exception_handler

    # cleanup argv
    args = args or sys.argv[1:]  # drop executable/script
    args = tuple(ensure_text_type(s) for s in args)

    return conda_exception_handler(main_inner, *args, **kwargs)
