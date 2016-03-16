# (c) 2012-2013 Continuum Analytics, Inc. / http://continuum.io
# All Rights Reserved
#
# conda is distributed under the terms of the BSD 3-clause license.
# Consult LICENSE.txt or http://opensource.org/licenses/BSD-3-Clause.

from __future__ import print_function, division, absolute_import

from conda.cli import common, install


help = "Installs a list of packages into a specified conda environment."
descr = help + """

This command accepts a list of package specifications (e.g, bitarray=0.8)
and installs a set of packages consistent with those specifications and
compatible with the underlying environment. If full compatibility cannot
be assured, an error is reported and the environment is not changed.

Conda attempts to install the newest versions of the requested packages. To
accomplish this, it may update some packages that are already installed, or
install additional packages. To prevent existing packages from updating,
use the --no-update-deps option. This may force conda to install older
versions of the requested packages, and it does not prevent additional
dependency packages from being installed.

If you wish to skip dependency checking altogether, use the '--force'
option. This may result in an environment with incompatible packages, so
this option must be used with great caution.

conda can also be called with a list of explicit conda package filenames
(e.g. ./lxml-3.2.0-py27_0.tar.bz2). Using conda in this mode implies the
--force option, and should likewise be used with great caution. Explicit
filenames and package specifications cannot be mixed in a single command.
"""
example = """
Examples:

    conda install -n myenv scipy

"""

def configure_parser(sub_parsers):
    p = sub_parsers.add_parser(
        'install',
        description=descr,
        help=help,
        epilog=example,
    )
    p.add_argument(
        "--revision",
        action="store",
        help="Revert to the specified REVISION.",
        metavar='REVISION',
    )
    common.add_parser_install(p)
    common.add_parser_json(p)
    p.set_defaults(func=execute)


def execute(args, parser):
    install.install(args, parser, 'install')
