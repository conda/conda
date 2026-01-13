# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""CLI implementation for `conda-env update`.

Updates the conda environments with the specified packages.
"""

import os
from argparse import (
    ArgumentParser,
    Namespace,
    _SubParsersAction,
)

from ..notices import notices
from pathlib import Path


def configure_parser(sub_parsers: _SubParsersAction, **kwargs) -> ArgumentParser:
    from ..auxlib.ish import dals
    from .helpers import (
        add_parser_environment_specifier,
        add_parser_frozen_env,
        add_parser_solver,
        add_parser_create_install_update,
    )
    from ..common.path import expand

    summary = "Update the current environment based on environment file."
    description = summary
    epilog = dals(
        """
        Examples::

            conda env update
            conda env update -n=foo
            conda env update -f=/path/to/environment.yml
            conda env update --name=foo --file=environment.yml
            conda env update vader/deathstar

        """
    )

    p = sub_parsers.add_parser(
        "update",
        help=summary,
        description=description,
        epilog=epilog,
        **kwargs,
    )

    # Common args for create/install/update
    # Includes parser prefix, networking, output and prompt options
    add_parser_create_install_update(p)

    # Add environment spec plugin args
    add_parser_environment_specifier(p)

    add_parser_frozen_env(p)
    p.add_argument(
        "--prune",
        action="store_true",
        default=False,
        help="remove installed packages not defined in environment.yml",
    )

    add_parser_solver(p)

    # HACK: recreate the default environment file is `environment.yml` behaviour
    env_yml_default_file = Path(expand("environment.yml"))
    if env_yml_default_file.is_file():
        p.set_defaults(file=["environment.yml"])
   
    p.set_defaults(func="conda.cli.main_env_update.execute")

    return p


@notices
def execute(args: Namespace, parser: ArgumentParser) -> int:
    from ..auxlib.ish import dals
    from ..base.context import context, determine_target_prefix
    from ..core.prefix_data import PrefixData
    from ..exceptions import CondaEnvException, EnvironmentSpecPluginNotDetected
    from .common import validate_file_exists
    from .install import install
    import contextlib

    # validate incoming arguments
    for file in args.file:
        validate_file_exists(file)

    # HACK: get the name and prefix from the file if possible
    name = None
    prefix = None
    if args.file:
        # Validate incoming arguments
        for file in args.file:
            try:
                with contextlib.redirect_stdout(None):
                    # detect the file format and get the env representation
                    spec_hook = context.plugin_manager.get_environment_specifier(
                        source=file,
                        name=context.environment_specifier,
                    )
                    spec = spec_hook.environment_spec(file)
                    env = spec.env
                    # HACK: continued, get the name and prefix
                    name = name or env.name
                    prefix = prefix or env.prefix
            except EnvironmentSpecPluginNotDetected:
                pass
    # HACK: continued, set args.name and args.prefix
    if args.name is None:
        args.name = name
    if args.prefix is None and args.name is None:
        args.prefix = prefix

    if not (args.name or args.prefix):
        if not env.name:
            # Note, this is a hack for get_prefix that assumes argparse results
            # TODO Refactor common.get_prefix
            name = os.environ.get("CONDA_DEFAULT_ENV", False)
            if not name:
                msg = dals(
                    """
                    Unable to determine environment

                    Please re-run this command with one of the following options:

                    * Provide an environment name via --name or -n
                    * Provide an environment path via --prefix or -p
                    * Re-run this command inside an activated conda environment.
                    """
                )
                # TODO Add json support
                raise CondaEnvException(msg)

        # Note: stubbing out the args object as all of the
        # conda.cli.common code thinks that name will always
        # be specified.
        args.name = env.name

    prefix = determine_target_prefix(context, args)
    prefix_data = PrefixData(prefix)
    install_type = "install"
    if prefix_data.is_environment():
        prefix_data.assert_writable()
        if context.protect_frozen_envs:
            prefix_data.assert_not_frozen()
    else:
        install_type = "create"
    
    install(args, parser, install_type)
        
    return 0
