# -*- coding: utf-8 -*-
# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
from __future__ import annotations
import json
import os
import sys
from typing import TYPE_CHECKING
import textwrap

from ....base.context import context, determine_target_prefix
from ....cli import install as cli_install
from ....core.prefix_data import PrefixData
from ....exceptions import SpecNotFound
from ....gateways.disk.delete import rm_rf
from ....notices import notices
from ....misc import touch_nonadmin
from ..installers.base import InvalidInstaller, get_installer
from .. import specs
from .common import print_result, get_filename

if TYPE_CHECKING:
    from argparse import ArgumentParser, Namespace


@notices
def execute(args: Namespace, parser: ArgumentParser) -> None:
    name = args.remote_definition or args.name

    try:
        spec = specs.detect(name=name, filename=get_filename(args.file), directory=os.getcwd())
        env = spec.environment

        # FIXME conda code currently requires args to have a name or prefix
        # don't overwrite name if it's given. gh-254
        if args.prefix is None and args.name is None:
            args.name = env.name

    except SpecNotFound:
        raise

    prefix = determine_target_prefix(context, args)

    if args.force and prefix != context.root_prefix and os.path.exists(prefix):
        rm_rf(prefix)
    cli_install.check_prefix(prefix, json=args.json)

    # TODO, add capability
    # common.ensure_override_channels_requires_channel(args)
    # channel_urls = args.channel or ()

    result = {"conda": None, "pip": None}

    args_packages = context.create_default_packages if not args.no_default_packages else []

    if args.dry_run:
        installer_type = "conda"
        installer = get_installer(installer_type)

        pkg_specs = env.dependencies.get(installer_type, [])
        pkg_specs.extend(args_packages)

        solved_env = installer.dry_run(pkg_specs, args, env)
        if args.json:
            print(json.dumps(solved_env.to_dict(), indent=2))
        else:
            print(solved_env.to_yaml(), end="")

    else:
        if args_packages:
            installer_type = "conda"
            installer = get_installer(installer_type)
            result[installer_type] = installer.install(prefix, args_packages, args, env)

        if len(env.dependencies.items()) == 0:
            installer_type = "conda"
            pkg_specs = []
            installer = get_installer(installer_type)
            result[installer_type] = installer.install(prefix, pkg_specs, args, env)
        else:
            for installer_type, pkg_specs in env.dependencies.items():
                try:
                    installer = get_installer(installer_type)
                    result[installer_type] = installer.install(prefix, pkg_specs, args, env)
                except InvalidInstaller:
                    sys.stderr.write(
                        textwrap.dedent(
                            """
                        Unable to install package for {0}.

                        Please double check and ensure your dependencies file has
                        the correct spelling.  You might also try installing the
                        conda-env-{0} package to see if provides the required
                        installer.
                        """
                        )
                        .lstrip()
                        .format(installer_type)
                    )
                    return -1

        if env.variables:
            pd = PrefixData(prefix)
            pd.set_environment_env_vars(env.variables)

        touch_nonadmin(prefix)
        print_result(args, prefix, result)


if __name__ == "__main__":
    from ._parser import configure_parser

    parser = configure_parser()
    args = parser.parse_args()
    execute(args, parser)
