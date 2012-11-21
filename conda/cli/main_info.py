# (c) 2012 Continuum Analytics, Inc. / http://continuum.io
# All Rights Reserved
#
# conda is distributed under the terms of the BSD 3-clause license.
# Consult LICENSE.txt or http://opensource.org/licenses/BSD-3-Clause.

from config import config


def configure_parser(sub_parsers):
    p = sub_parsers.add_parser(
        'info',
        description     = "Display information about current Anaconda install.",
        help            = "Display information about current Anaconda install.",
    )
    p.set_defaults(func=execute)


def execute(args):

    conf = config()

    print
    print "Current Anaconda install:"
    print conf
    print

