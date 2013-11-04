# (c) 2012-2013 Continuum Analytics, Inc. / http://continuum.io
# All Rights Reserved
#
# conda is distributed under the terms of the BSD 3-clause license.
# Consult LICENSE.txt or http://opensource.org/licenses/BSD-3-Clause.

from __future__ import print_function, division, absolute_import

import re
import sys
from os.path import isdir, join
import subprocess

import conda.install as install
import conda.config as config
from conda.cli import common


descr = "List linked packages in a conda environment."


def configure_parser(sub_parsers):
    p = sub_parsers.add_parser(
        'list',
        description = descr,
        help = descr,
    )
    common.add_parser_prefix(p)
    p.add_argument(
        '-c', "--canonical",
        action = "store_true",
        help = "output canonical names of packages only",
    )
    p.add_argument(
        '-e', "--export",
        action = "store_true",
        help = "output requirement string only "
                  "(output may be used by conda create --file)",
    )
    p.add_argument(
        "--no-pip",
        action = "store_false",
        default=True,
        dest="pip",
        help = "Do not include pip-only installed packages")
    p.add_argument(
        'regex',
        action = "store",
        nargs = "?",
        help = "list only packages matching this regular expression",
    )
    p.set_defaults(func=execute)


def print_export_header():
    print('# This file may be used to create an environment using:')
    print('# $ conda create --name <env> --file <this file>')
    print('# platform: %s' % config.subdir)


def _linked(prefix, piplist):
    installed = install.linked(prefix)
    if piplist:
        pip_path = join(prefix,'bin','pip')
        try:
            pipinst = subprocess.check_output([pip_path,'list']).split('\n')
        except Exception as e:
            # Any error should just be ignored
            print("Could not run pip to get pip-installed packages")
            print("Not a problem: no pip-installed packages will be listed")
            return installed
        # For every package in pipinst that is not already represented
        # in installed append a fake name to installed with 'pip'
        # as the build string
        for pkg in pipinst:
            if not pkg:
                continue
            name, version = pkg.split()
            name = name.lower()
            # remove '()'
            version = version[1:-1]
            # This search could be made faster with a sorted 
            # list and binary search
            # The matching is not always perfect
            found = False
            for condapkg in installed:
                cname, cversion = condapkg.rsplit('-',2)[:2]
                if name == cname and version == cversion:
                    found = True
                    break
            if not found:
                installed.add('%s-%s-*pip*'%(name, version))

    return installed

def _is_linked(prefix, dist, piplist):
    pass

def list_packages(prefix, regex=None, format='human', piplist=True):
    if not isdir(prefix):
        sys.exit("""\
Error: environment does not exist: %s
#
# Use 'conda create' to create an environment before listing its packages.""" % prefix)
    pat = re.compile(regex, re.I) if regex else None

    if format == 'human':
        print('# packages in environment at %s:' % prefix)
        print('#')
        res = 1
    if format == 'export':
        print_export_header()

    for dist in sorted(_linked(prefix, piplist)):
        name = dist.rsplit('-', 2)[0]
        if pat and pat.search(name) is None:
            continue
        res = 0
        if format == 'canonical':
            print(dist)
            continue
        if format == 'export':
            print('='.join(dist.rsplit('-', 2)))
            continue
        try:
            # Returns None if no meta-file found (e.g. pip install)
            info = install.is_linked(prefix, dist)
            features = set(info.get('features', '').split())
            print('%-25s %-15s %15s  %s' % (info['name'],
                                            info['version'],
                                            info['build'],
                                            common.disp_features(features)))
        except: # IOError, KeyError, ValueError
            print('%-25s %-15s %15s' % tuple(dist.rsplit('-', 2)))

    return res


def execute(args, parser):
    prefix = common.get_prefix(args)

    if args.canonical:
        format = 'canonical'
    elif args.export:
        format = 'export'
    else:
        format = 'human'
    sys.exit(list_packages(prefix, args.regex, format=format, piplist=args.pip))
