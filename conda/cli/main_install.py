# (c) 2012-2013 Continuum Analytics, Inc. / http://continuum.io
# All Rights Reserved
#
# conda is distributed under the terms of the BSD 3-clause license.
# Consult LICENSE.txt or http://opensource.org/licenses/BSD-3-Clause.

from __future__ import print_function, division, absolute_import

from argparse import RawDescriptionHelpFormatter
import os
import sys

from conda.cli import common, install
try:
    from conda_env.env import load_from_directory
    from conda_env import exceptions
    conda_env_installed = True
except ImportError:
    conda_env_installed = False


help = "Install a list of packages into a specified conda environment."
descr = help + """
The arguments may be packages specifications (e.g. bitarray=0.8),
or explicit conda packages filenames (e.g. ./lxml-3.2.0-py27_0.tar.bz2) which
must exist on the local filesystem.  The two types of arguments cannot be
mixed and the latter implies the --force and --no-deps options.
"""
example = """
examples:
    conda install -n myenv scipy

"""

def configure_parser(sub_parsers):
    p = sub_parsers.add_parser(
        'install',
        formatter_class = RawDescriptionHelpFormatter,
        description = descr,
        help = help,
        epilog = example,
    )
    p.add_argument(
        "--revision",
        action = "store",
        help = "revert to the specified REVISION",
        metavar = 'REVISION',
    )
    common.add_parser_install(p)
    common.add_parser_json(p)

    if conda_env_installed:
        p.add_argument(
            '--save',
            action='store_true',
            help='add dependency to environment.yml file',
        )

    p.set_defaults(func=execute)


def execute(args, parser):
    install.install(args, parser, 'install')
    if conda_env_installed and args.save:
        try:
            env = load_from_directory(os.getcwd())
            for pkg in args.packages:
                env.dependencies.add(pkg)
            env.save()
        except exceptions.EnvironmentFileNotFound:
            if not args.json:
                sys.stderr.write(
                    "WARNING: Unable to find environment.yml file. "
                    "Skipping save.\n"
                )
