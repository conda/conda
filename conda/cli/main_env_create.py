# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""CLI implementation for `conda-env create`.

Creates new conda environments with the specified packages.
"""

from argparse import (
    ArgumentParser,
    Namespace,
    _SubParsersAction,
)
from pathlib import Path

from ..cli.main_config import set_keys
from ..notices import notices


def configure_parser(sub_parsers: _SubParsersAction, **kwargs) -> ArgumentParser:
    from ..auxlib.ish import dals
    from .helpers import (
        add_parser_default_packages,
        add_parser_environment_specifier,
        add_parser_platform,
        add_parser_solver,
        add_parser_create_install_update,
    )
    from ..common.path import expand

    summary = "Create an environment based on an environment definition file."
    description = dals(
        f"""
        {summary}

        If using an environment.yml file (the default), you can name the
        environment in the first line of the file with 'name: envname' or
        you can specify the environment name in the CLI command using the
        -n/--name argument. The name specified in the CLI will override
        the name specified in the environment.yml file.

        Unless you are in the directory containing the environment definition
        file, use -f to specify the file path of the environment definition
        file you want to use.

        """
    )
    epilog = dals(
        """
        Examples::

            conda env create
            conda env create -n envname
            conda env create folder/envname
            conda env create -f /path/to/environment.yml
            conda env create -f /path/to/requirements.txt -n envname
            conda env create -f /path/to/requirements.txt -p /home/user/envname

        """
    )

    p = sub_parsers.add_parser(
        "create",
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

    add_parser_default_packages(p)
    add_parser_solver(p)
    add_parser_platform(p)

    # HACK: recreate the default environment file is `environment.yml` behaviour
    env_yml_default_file = Path(expand("environment.yml"))
    if env_yml_default_file.is_file():
        p.set_defaults(file=["environment.yml"])
   
    p.set_defaults(
        func="conda.cli.main_env_create.execute",
        clone=False,
    )

    return p


@notices
def execute(args: Namespace, parser: ArgumentParser) -> int:
    from ..exceptions import EnvironmentFileNotFound, EnvironmentSpecPluginNotDetected
    from .common import validate_file_exists
    from .install import install
    from ..base.context import context
    import contextlib

    if args.file:
        for file in args.file:
            validate_file_exists(file)
    else:
        raise EnvironmentFileNotFound(filename="")
    
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

    install(args, parser, "create")
    return 0
