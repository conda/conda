# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
from argparse import ArgumentParser
from contextlib import contextmanager
from tempfile import mkdtemp

from conda.cli.main_env import execute as execute_conda_env
from conda.cli.main_env_create import configure_parser as create_configure_parser
from conda.cli.main_env_update import configure_parser as update_configure_parser
from conda.cli.main_export import configure_parser as export_configure_parser
from conda.deprecations import deprecated
from conda.gateways.disk.delete import rm_rf
from conda.utils import massage_arguments


class Commands:
    CREATE = "create"
    UPDATE = "update"
    EXPORT = "export"


parser_config = {
    Commands.CREATE: create_configure_parser,
    Commands.UPDATE: update_configure_parser,
    Commands.EXPORT: export_configure_parser,
}


@contextmanager
def make_temp_envs_dir():
    envs_dir = mkdtemp()
    try:
        yield envs_dir
    finally:
        rm_rf(envs_dir)


@deprecated("24.3", "24.9", addendum="Use `conda.testing.conda_cli` instead.")
def run_command(command, env_name, *arguments):
    arguments = massage_arguments(arguments)
    args = [command, "-n", env_name, "-f"] + arguments

    p = ArgumentParser()
    sub_parsers = p.add_subparsers(metavar="command", dest="cmd")
    parser_config[command](sub_parsers)
    args = p.parse_args(args)

    execute_conda_env(args, p)
