# (c) 2012-2013 Continuum Analytics, Inc. / http://continuum.io
# All Rights Reserved
#
# conda is distributed under the terms of the BSD 3-clause license.
# Consult LICENSE.txt or http://opensource.org/licenses/BSD-3-Clause.

from __future__ import absolute_import, division, print_function, unicode_literals

from .common import add_parser_install, add_parser_json
from .install import install
from ..gateways.disk.delete import delete_trash

help = "Updates conda packages to the latest compatible version."
descr = help + """

This command accepts a list of package names and updates them to the latest
versions that are compatible with all other packages in the environment.

Conda attempts to install the newest versions of the requested packages. To
accomplish this, it may update some packages that are already installed, or
install additional packages. To prevent existing packages from updating,
use the --no-update-deps option. This may force conda to install older
versions of the requested packages, and it does not prevent additional
dependency packages from being installed.

If you wish to skip dependency checking altogether, use the '--force'
option. This may result in an environment with incompatible packages, so
this option must be used with great caution.
"""
example = """
Examples:

    conda %s -n myenv scipy

"""

alias_help = "Alias for conda update.  See conda update --help."

def configure_parser(sub_parsers, name='update'):
    if name == 'update':
        p = sub_parsers.add_parser(
            'update',
            description=descr,
            help=descr,
            epilog=example % name,
        )
    else:
        p = sub_parsers.add_parser(
            name,
            description=alias_help,
            help=alias_help,
            epilog=example % name,
        )
    add_parser_install(p)
    add_parser_json(p)
    p.add_argument(
        "--all",
        action="store_true",
        help="Update all installed packages in the environment.",
    )
    p.set_defaults(func=execute)


def execute(args, parser):
    install(args, parser, 'update')
    delete_trash()
