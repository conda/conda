# -*- coding: utf-8 -*-
# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
from __future__ import annotations
import os
import sys
import textwrap
from typing import TYPE_CHECKING

from ....base.context import context, determine_target_prefix
from ....core.prefix_data import PrefixData
from ....exceptions import CondaEnvException, SpecNotFound
from ....misc import touch_nonadmin
from ....notices import notices
from ....env import specs
from ....env.installers.base import InvalidInstaller, get_installer
from ..common import print_result, get_filename

if TYPE_CHECKING:
    from argparse import ArgumentParser, Namespace


@notices
def execute(args: Namespace, parser: ArgumentParser) -> None:
    name = args.remote_definition or args.name

    try:
        spec = specs.detect(name=name, filename=get_filename(args.file), directory=os.getcwd())
        env = spec.environment
    except SpecNotFound:
        raise

    if not (args.name or args.prefix):
        if not env.name:
            # Note, this is a hack fofr get_prefix that assumes argparse results
            # TODO Refactor common.get_prefix
            name = os.environ.get("CONDA_DEFAULT_ENV", False)
            if not name:
                msg = "Unable to determine environment\n\n"
                msg += textwrap.dedent(
                    """
                    Please re-run this command with one of the following options:

                    * Provide an environment name via --name or -n
                    * Re-run this command inside an activated conda environment."""
                ).lstrip()
                # TODO Add json support
                raise CondaEnvException(msg)

        # Note: stubbing out the args object as all of the
        # conda.cli.common code thinks that name will always
        # be specified.
        args.name = env.name

    prefix = determine_target_prefix(context, args)
    # CAN'T Check with this function since it assumes we will create prefix.
    # cli_install.check_prefix(prefix, json=args.json)

    # TODO, add capability
    # common.ensure_override_channels_requires_channel(args)
    # channel_urls = args.channel or ()

    # create installers before running any of them
    # to avoid failure to import after the file being deleted
    # e.g. due to conda_env being upgraded or Python version switched.
    installers = {}

    for installer_type in env.dependencies:
        try:
            installers[installer_type] = get_installer(installer_type)
        except InvalidInstaller:
            sys.stderr.write(
                textwrap.dedent(
                    """
                Unable to install package for {0}.

                Please double check and ensure you dependencies file has
                the correct spelling.  You might also try installing the
                conda-env-{0} package to see if provides the required
                installer.
                """
                )
                .lstrip()
                .format(installer_type)
            )
            return -1

    result = {"conda": None, "pip": None}
    for installer_type, pkg_specs in env.dependencies.items():
        installer = installers[installer_type]
        result[installer_type] = installer.install(prefix, pkg_specs, args, env)

    if env.variables:
        pd = PrefixData(prefix)
        pd.set_environment_env_vars(env.variables)

    touch_nonadmin(prefix)
    print_result(args, prefix, result)


if __name__ == "__main__":
    from ...argparse import do_call
    from ._parser import configure_parser

    parser = configure_parser()
    args = parser.parse_args()
    do_call(args, parser)
