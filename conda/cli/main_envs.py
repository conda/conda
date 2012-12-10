# (c) 2012 Continuum Analytics, Inc. / http://continuum.io
# All Rights Reserved
#
# conda is distributed under the terms of the BSD 3-clause license.
# Consult LICENSE.txt or http://opensource.org/licenses/BSD-3-Clause.

from conda.config import config


def configure_parser(sub_parsers):
    p = sub_parsers.add_parser(
        'envs',
        description     = "List all known Anaconda environments.",
        help            = "List all known Anaconda environments.",
    )
    p.set_defaults(func=execute)


def execute(args):
    conf = config()

    envs = conf.environments

    print "Known Anaconda environments:"
    print

    for env in envs:
        print "    %s" % env.prefix
    print

