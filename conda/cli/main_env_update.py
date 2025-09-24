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

from .. import CondaError
from ..notices import notices


def configure_parser(sub_parsers: _SubParsersAction, **kwargs) -> ArgumentParser:
    from ..auxlib.ish import dals
    from .helpers import (
        add_parser_environment_specifier,
        add_parser_frozen_env,
        add_parser_json,
        add_parser_prefix,
        add_parser_solver,
    )

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

    # Add environment spec plugin args
    add_parser_environment_specifier(p)

    add_parser_frozen_env(p)
    add_parser_prefix(p)
    p.add_argument(
        "-f",
        "--file",
        action="store",
        help="environment definition (default: environment.yml)",
        default="environment.yml",
    )
    p.add_argument(
        "--prune",
        action="store_true",
        default=False,
        help="remove installed packages not defined in environment.yml",
    )

    add_parser_json(p)
    add_parser_solver(p)
    p.set_defaults(func="conda.cli.main_env_update.execute")

    return p


@notices
def execute(args: Namespace, parser: ArgumentParser) -> int:
    from ..auxlib.ish import dals
    from ..base.context import context, determine_target_prefix
    from ..core.prefix_data import PrefixData
    from ..env.env import print_result
    from ..env.installers.base import get_installer
    from ..exceptions import CondaEnvException, InvalidInstaller
    from .common import validate_file_exists

    # validate incoming arguments
    validate_file_exists(args.file)

    # detect the file format and get the env representation
    spec_hook = context.plugin_manager.get_environment_specifier(
        source=args.file,
        name=context.environment_specifier,
    )
    spec = spec_hook.environment_spec(args.file)
    env = spec.env

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
    if prefix_data.is_environment():
        prefix_data.assert_writable()
        if context.protect_frozen_envs:
            prefix_data.assert_not_frozen()

    # CAN'T Check with this function since it assumes we will create prefix.
    # cli_install.check_prefix(prefix, json=args.json)

    # TODO, add capability
    # common.ensure_override_channels_requires_channel(args)
    # channel_urls = args.channel or ()

    # create installers before running any of them
    # to avoid failure to import after the file being deleted
    # e.g. due to conda_env being upgraded or Python version switched.
    installers = {}

    if env.requested_packages:
        installers["conda"] = get_installer("conda")

    for installer_type in env.external_packages:
        try:
            installers[installer_type] = get_installer(installer_type)
        except InvalidInstaller:
            raise CondaError(
                dals(
                    f"""
                    Unable to install package for {0}.

                    Please double check and ensure you dependencies file has
                    the correct spelling.  You might also try installing the
                    conda-env-{0} package to see if provides the required
                    installer.
                    """
                )
            )

            return -1

    result = {"conda": None, "pip": None}
    # install conda packages
    installer_type = "conda"
    installer = installers[installer_type]
    result[installer_type] = installer.install(
        prefix, env.requested_packages, args, env
    )
    # install all other external packages
    for installer_type, specs in env.external_packages.items():
        installer = installers[installer_type]
        result[installer_type] = installer.install(prefix, specs, args, env)

    if env.variables:
        prefix_data.set_environment_env_vars(env.variables)

    prefix_data.set_nonadmin()
    print_result(args, prefix, result)

    return 0
