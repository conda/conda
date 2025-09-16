# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause

from conda.cli.main_env_create import configure_parser as create_configure_parser
from conda.cli.main_env_update import configure_parser as update_configure_parser
from conda.cli.main_export import configure_parser as export_configure_parser


class Commands:
    CREATE = "create"
    UPDATE = "update"
    EXPORT = "export"


parser_config = {
    Commands.CREATE: create_configure_parser,
    Commands.UPDATE: update_configure_parser,
    Commands.EXPORT: export_configure_parser,
}
