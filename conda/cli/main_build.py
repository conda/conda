# (c) 2012 Continuum Analytics, Inc. / http://continuum.io
# All Rights Reserved
#
# conda is distributed under the terms of the BSD 3-clause license.
# Consult LICENSE.txt or http://opensource.org/licenses/BSD-3-Clause.

import sys
from os.path import isdir, isfile

from conda.builder.commands import build
from utils import add_parser_prefix, get_prefix


descr = "Build a package from source. (EXPERIMENTAL)"

source_types = 'git', 'tar', 'zip', 'svn', 'dir'

def configure_parser(sub_parsers):
    p = sub_parsers.add_parser('build', description=descr, help=descr)
    npgroup = p.add_mutually_exclusive_group()
    npgroup.add_argument("--git",
                         action="store_true",
                         help="build from git url")
    npgroup.add_argument("--tar",
                         action="store_true",
                         help="build from local source tarball")
    npgroup.add_argument("--zip",
                         action="store_true",
                         help="build from local source zipfile")
    npgroup.add_argument("--svn",
                         action="store_true",
                         help = "build from svn")
    npgroup.add_argument("--dir",
                         action="store_true",
                         help="build from local source directory")
    add_parser_prefix(p)
    p.add_argument('url',
                   action="store",
                   metavar='URL',
                   nargs=1,
                   help="name of source (url, tarball, path, etc...)",
    )
    p.set_defaults(func=execute)


def get_source_type(args, parser):
    for opt_name in source_types:
        if getattr(args, opt_name):
            return opt_name
    # try to determine source from url
    url = args.url[0]
    if isfile(url):
        if url.endswith(('.tar.gz', '.tar.bz2', '.tgz', '.tar')):
            return 'tar'
        if url.endswith('.zip'):
            return 'zip'
    if isdir(url):
        return 'dir'
    if url.endswith('.git'):
        return 'git'
    # we don't know
    return None


def execute(args):
    prefix = get_prefix(args)
    source_type = get_source_type(args)
    if source_type is None:
        sys.exit('Error: Could not determine source type, please provide one\n'
                 'of the following options: %s' %
                 ', '.join('--' + s for s in source_types))

    build(prefix, args.url[0], source_type)
