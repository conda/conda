# (c) 2012 Continuum Analytics, Inc. / http://continuum.io
# All Rights Reserved
#
# conda is distributed under the terms of the BSD 3-clause license.
# Consult LICENSE.txt or http://opensource.org/licenses/BSD-3-Clause.

from conda.builder.commands import pip
from utils import add_parser_prefix, get_prefix

descr = "Build a package from source. (EXPERIMENTAL)"


def configure_parser(sub_parsers):
    p = sub_parsers.add_parser('build', description=descr, help=descr)
    npgroup = p.add_mutually_exclusive_group()
    npgroup.add_argument("--git",
                         action="store_true",
                         help="build from git")
    npgroup.add_argument("--tar",
                         action="store_true",
                         help="build from source tarball")
    npgroup.add_argument("--zip",
                         action="store_true",
                         help="build from source zipfile")
    npgroup.add_argument("--svn",
                         action="store_true",
                         help = "build from svn")
    npgroup.add_argument("--dir",
                         action = "store_true",
                         help="build from local source directoriy")
    add_parser_prefix(p)
    p.add_argument(
        'url',
        action  = "store",
        metavar = 'url',
        nargs   = 1,
        help    = "name of source (url, tarball, path, etc...)",
    )
    p.set_defaults(func=execute)


def get_source_type(args):
    if args.git:
        return 'git'
    if args.tar:
        return 'tar'
    if args.zip:
        return 'zip'
    if args.svn:
        return 'svn'
    if args.dir:
        return 'dir'
    # try to determine source from url
    url = args.url[0]
    # TODO...
    #if url.ends


def execute(args):
    prefix = get_prefix(args)
    source_type = get_source_type(args)
    print 'source_type:', source_type
