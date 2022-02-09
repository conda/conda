# -*- coding: utf-8 -*-
# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
from __future__ import print_function

from argparse import RawDescriptionHelpFormatter
import json
import os
import sys
import textwrap

from conda.cli import install as cli_install
from conda.cli.conda_argparse import add_parser_default_packages, add_parser_json, \
    add_parser_prefix, add_parser_networking, add_parser_experimental_solver
from conda.core.prefix_data import PrefixData
from conda.gateways.disk.delete import rm_rf
from conda.misc import touch_nonadmin
from .common import get_prefix, print_result, get_filename
from .. import exceptions, specs
from ..installers.base import InvalidInstaller, get_installer

description = """
Create an environment based on an environment file
"""

example = """
examples:
    conda env create
    conda env create -n name
    conda env create vader/deathstar
    conda env create -f=/path/to/environment.yml
    conda env create -f=/path/to/requirements.txt -n deathstar
    conda env create -f=/path/to/requirements.txt -p /home/user/software/deathstar
"""


def configure_parser(sub_parsers):
    p = sub_parsers.add_parser(
        'create',
        formatter_class=RawDescriptionHelpFormatter,
        description=description,
        help=description,
        epilog=example,
    )
    p.add_argument(
        '-f', '--file',
        action='store',
        help='environment definition file (default: environment.yml)',
        default='environment.yml',
    )

    # Add name and prefix args
    add_parser_prefix(p)

    # Add networking args
    add_parser_networking(p)

    p.add_argument(
        'remote_definition',
        help='remote environment definition / IPython notebook',
        action='store',
        default=None,
        nargs='?'
    )
    p.add_argument(
        '--force',
        help=('force creation of environment (removing a previously existing '
              'environment of the same name).'),
        action='store_true',
        default=False,
    )
    p.add_argument(
        '-d', '--dry-run',
        help='Only display what would have been done.',
        action='store_true',
        default=False
    )
    add_parser_default_packages(p)
    add_parser_json(p)
    add_parser_experimental_solver(p)
    p.set_defaults(func='.main_create.execute')


def execute(args, parser):
    from conda.base.context import context
    name = args.remote_definition or args.name

    try:
        spec = specs.detect(name=name, filename=get_filename(args.file), directory=os.getcwd())
        env = spec.environment

        # FIXME conda code currently requires args to have a name or prefix
        # don't overwrite name if it's given. gh-254
        if args.prefix is None and args.name is None:
            args.name = env.name

    except exceptions.SpecNotFound:
        raise

    prefix = get_prefix(args, search=False)

    if args.force and prefix != context.root_prefix and os.path.exists(prefix):
        rm_rf(prefix)
    cli_install.check_prefix(prefix, json=args.json)

    # TODO, add capability
    # common.ensure_override_channels_requires_channel(args)
    # channel_urls = args.channel or ()

    result = {"conda": None, "pip": None}

    args_packages = context.create_default_packages if not args.no_default_packages else []

    if args.dry_run:
        installer_type = 'conda'
        installer = get_installer(installer_type)

        pkg_specs = env.dependencies.get(installer_type, [])
        pkg_specs.extend(args_packages)

        solved_env = installer.dry_run(pkg_specs, args, env)
        if args.json:
            print(json.dumps(solved_env.to_dict(), indent=2))
        else:
            print(solved_env.to_yaml(), end='')

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
                    sys.stderr.write(textwrap.dedent("""
                        Unable to install package for {0}.

                        Please double check and ensure your dependencies file has
                        the correct spelling.  You might also try installing the
                        conda-env-{0} package to see if provides the required
                        installer.
                        """).lstrip().format(installer_type)
                    )
                    return -1

        if env.variables:
            pd = PrefixData(prefix)
            pd.set_environment_env_vars(env.variables)

        touch_nonadmin(prefix)
        print_result(args, prefix, result)
