# (c) 2012 Continuum Analytics, Inc. / http://continuum.io
# All Rights Reserved
#
# conda is distributed under the terms of the BSD 3-clause license.
# Consult LICENSE.txt or http://opensource.org/licenses/BSD-3-Clause.

from config import config

def configure_parser(sub_parsers):
    p = sub_parsers.add_parser(
        'locations',
        description = "List known locations for Anaconda environments.",
        help        = "List known locations for Anaconda environments.",
    )
    p.set_defaults(func=execute)


def execute(args):
    conf = config()

    print "System location for Anaconda environments:"
    print
    print '    %s' % conf.system_location

    if conf.user_locations:
        print
        print "User locations for Anaconda environments:"
        print
        for location in conf.user_locations:
            print "    %s" % location
        print



