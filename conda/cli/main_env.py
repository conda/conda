# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""Entry point for all conda-env subcommands."""
import sys
from argparse import ArgumentParser
from importlib import import_module

import conda.exports  # noqa
from conda.base.context import context

from . import (
    main_env_config,
    main_env_create,
    main_env_export,
    main_env_list,
    main_env_remove,
    main_env_update,
)


def configure_parser():
    p = ArgumentParser()
    sub_parsers = p.add_subparsers(
        metavar="command",
        dest="cmd",
    )
    main_env_create.configure_parser(sub_parsers)
    main_env_export.configure_parser(sub_parsers)
    main_env_list.configure_parser(sub_parsers)
    main_env_remove.configure_parser(sub_parsers)
    main_env_update.configure_parser(sub_parsers)
    main_env_config.configure_parser(sub_parsers)

    if len(sys.argv) == 1:  # sys.argv == ['/path/to/bin/conda-env']
        sys.argv.append("--help")

    return p


def execute(args, parser):
    relative_mod, func_name = args.func.rsplit(".", 1)

    # Run the pre_command actions
    command = relative_mod.replace(".main_", "")

    context.plugin_manager.invoke_pre_commands(f"env_{command}")
    module = import_module(relative_mod, "conda_env.cli")
    exit_code = getattr(module, func_name)(args, parser)
    context.plugin_manager.invoke_post_commands(f"env_{command}")

    return exit_code
