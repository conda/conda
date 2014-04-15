# (c) Continuum Analytics, Inc. / http://continuum.io
# All Rights Reserved
#
# conda is distributed under the terms of the BSD 3-clause license.
# Consult LICENSE.txt or http://opensource.org/licenses/BSD-3-Clause.

from __future__ import print_function, division, absolute_import

import re
import sys
import subprocess
from os.path import isdir, isfile, join

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
        '-r', "--revisions",
        action = "store_true",
        help = "list the revision history and exit",
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


def pip_args(prefix):
    """
    return the arguments required to invoke pip (in prefix), or None if pip
    is not installed
    """
    if sys.platform == 'win32':
        pip_path = join(prefix, 'Scripts', 'pip-script.py')
        py_path = join(prefix, 'python.exe')
    else:
        pip_path = join(prefix, 'bin', 'pip')
        py_path = join(prefix, 'bin', 'python')
    if isfile(pip_path) and isfile(py_path):
        return [py_path, pip_path]
    else:
        return None


def add_pip_installed(prefix, installed):
    args = pip_args(prefix)
    if args is None:
        return
    args.append('list')
    try:
        pipinst = subprocess.check_output(
                                args, universal_newlines=True).split('\n')
    except Exception as e:
        # Any error should just be ignored
        print("# Warning: subprocess call to pip failed")
        return

    # For every package in pipinst that is not already represented
    # in installed append a fake name to installed with 'pip'
    # as the build string
    conda_names = {d.rsplit('-', 2)[0] for d in installed}
    pat = re.compile('([\w.-]+)\s+\(([\w.]+)')
    for line in pipinst:
        line = line.strip()
        if not line:
            continue
        m = pat.match(line)
        if m is None:
            print('Could not extract name and version from: %r' % line)
            continue
        name, version = m.groups()
        name = name.lower()
        if name not in conda_names:
            installed.add('%s-%s-<pip>' % (name, version))


def list_packages(prefix, regex=None, format='human', piplist=False):
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

    installed = install.linked(prefix)
    if piplist and config.use_pip and format == 'human':
        add_pip_installed(prefix, installed)

    for dist in sorted(installed):
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
            disp = '%(name)-25s %(version)-15s %(build)15s' % info
            disp += '  %s' % common.disp_features(features)
            if config.show_channel_urls:
                disp += '  %s' % config.canonical_channel_name(info.get('url'))
            print(disp)
        except: # (IOError, KeyError, ValueError):
            print('%-25s %-15s %15s' % tuple(dist.rsplit('-', 2)))

    return res


def execute(args, parser):
    prefix = common.get_prefix(args)

    if args.revisions:
        from conda.history import History

        h = History(prefix)
        if isfile(h.path):
            h.print_log()
        else:
            sys.stderr.write("No revision log found: %s\n" % h.path)
        return

    if args.canonical:
        format = 'canonical'
    elif args.export:
        format = 'export'
    else:
        format = 'human'
    sys.exit(list_packages(prefix, args.regex, format=format, piplist=args.pip))
