# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
from contextlib import contextmanager
from tempfile import mkdtemp

from conda.cli.main_env_create import configure_parser as create_configure_parser
from conda.cli.main_env_update import configure_parser as update_configure_parser
from conda.cli.main_export import configure_parser as export_configure_parser
from conda.gateways.disk.delete import rm_rf


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
