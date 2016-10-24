# (c) Continuum Analytics, Inc. / http://continuum.io
# All Rights Reserved
#
# conda is distributed under the terms of the BSD 3-clause license.
# Consult LICENSE.txt or http://opensource.org/licenses/BSD-3-Clause.

# NOTE:
#     This module is deprecated.  Don't import from this here when writing
#     new code.
from __future__ import absolute_import, division, print_function, unicode_literals

import hashlib
import json
import os
import re
import shutil
import tarfile
import tempfile
from conda._vendor.auxlib.entity import EntityEncoder
from conda.core.linked_data import is_linked, linked_data
from conda.core.linked_data import linked
from os.path import basename, dirname, isfile, islink, join, abspath, isdir

from ..base.context import context, get_prefix

from .common import add_parser_prefix
from ..common.compat import PY3, itervalues
from ..install import PREFIX_PLACEHOLDER
from ..misc import untracked


descr = "Low-level conda package utility. (EXPERIMENTAL)"


def configure_parser(sub_parsers):
    p = sub_parsers.add_parser(
        'package',
        description=descr,
        help=descr,
    )
    add_parser_prefix(p)
    p.add_argument(
        '-w', "--which",
        metavar="PATH",
        nargs='+',
        action="store",
        help="Given some PATH print which conda package the file came from.",
    )
    p.add_argument(
        '-r', "--reset",
        action="store_true",
        help="Remove all untracked files and exit.",
    )
    p.add_argument(
        '-u', "--untracked",
        action="store_true",
        help="Display all untracked files and exit.",
    )
    p.add_argument(
        "--pkg-name",
        action="store",
        default="unknown",
        help="Package name of the created package.",
    )
    p.add_argument(
        "--pkg-version",
        action="store",
        default="0.0",
        help="Package version of the created package.",
    )
    p.add_argument(
        "--pkg-build",
        action="store",
        default=0,
        help="Package build number of the created package.",
    )
    p.set_defaults(func=execute)


def remove(prefix, files):
    """
    Remove files for a given prefix.
    """
    dst_dirs = set()
    for f in files:
        dst = join(prefix, f)
        dst_dirs.add(dirname(dst))
        os.unlink(dst)

    for path in sorted(dst_dirs, key=len, reverse=True):
        try:
            os.rmdir(path)
        except OSError:  # directory might not be empty
            pass


def execute(args, parser):
    prefix = get_prefix(context, args)

    if args.which:
        for path in args.which:
            for dist in which_package(path):
                print('%-50s  %s' % (path, dist))
        return

    print('# prefix:', prefix)

    if args.reset:
        remove(prefix, untracked(prefix))
        return

    if args.untracked:
        files = sorted(untracked(prefix))
        print('# untracked files: %d' % len(files))
        for fn in files:
            print(fn)
        return

    make_tarbz2(prefix,
                name=args.pkg_name.lower(),
                version=args.pkg_version,
                build_number=int(args.pkg_build))


def get_installed_version(prefix, name):
    for info in itervalues(linked_data(prefix)):
        if info['name'] == name:
            return str(info['version'])
    return None


def create_info(name, version, build_number, requires_py):
    d = dict(
        name=name,
        version=version,
        platform=context.platform,
        arch=context.arch_name,
        build_number=int(build_number),
        build=str(build_number),
        depends=[],
    )
    if requires_py:
        d['build'] = ('py%d%d_' % requires_py) + d['build']
        d['depends'].append('python %d.%d*' % requires_py)
    return d


shebang_pat = re.compile(r'^#!.+$', re.M)
def fix_shebang(tmp_dir, path):
    if open(path, 'rb').read(2) != '#!':
        return False

    with open(path) as fi:
        data = fi.read()
    m = shebang_pat.match(data)
    if not (m and 'python' in m.group()):
        return False

    data = shebang_pat.sub('#!%s/bin/python' % PREFIX_PLACEHOLDER,
                           data, count=1)
    tmp_path = join(tmp_dir, basename(path))
    with open(tmp_path, 'w') as fo:
        fo.write(data)
    os.chmod(tmp_path, int('755', 8))
    return True


def _add_info_dir(t, tmp_dir, files, has_prefix, info):
    info_dir = join(tmp_dir, 'info')
    os.mkdir(info_dir)
    with open(join(info_dir, 'files'), 'w') as fo:
        for f in files:
            fo.write(f + '\n')

    with open(join(info_dir, 'index.json'), 'w') as fo:
        json.dump(info, fo, indent=2, sort_keys=True, cls=EntityEncoder)

    if has_prefix:
        with open(join(info_dir, 'has_prefix'), 'w') as fo:
            for f in has_prefix:
                fo.write(f + '\n')

    for fn in os.listdir(info_dir):
        t.add(join(info_dir, fn), 'info/' + fn)


def create_conda_pkg(prefix, files, info, tar_path, update_info=None):
    """
    create a conda package with `files` (in `prefix` and `info` metadata)
    at `tar_path`, and return a list of warning strings
    """
    files = sorted(files)
    warnings = []
    has_prefix = []
    tmp_dir = tempfile.mkdtemp()
    t = tarfile.open(tar_path, 'w:bz2')
    h = hashlib.new('sha1')
    for f in files:
        assert not (f.startswith('/') or f.endswith('/') or
                    '\\' in f or f == ''), f
        path = join(prefix, f)
        if f.startswith('bin/') and fix_shebang(tmp_dir, path):
            path = join(tmp_dir, basename(path))
            has_prefix.append(f)
        t.add(path, f)
        h.update(f.encode('utf-8'))
        h.update(b'\x00')
        if islink(path):
            link = os.readlink(path)
            if PY3 and isinstance(link, str):
                h.update(bytes(link, 'utf-8'))
            else:
                h.update(link)
            if link.startswith('/'):
                warnings.append('found symlink to absolute path: %s -> %s' %
                                (f, link))
        elif isfile(path):
            h.update(open(path, 'rb').read())
            if path.endswith('.egg-link'):
                warnings.append('found egg link: %s' % f)

    info['file_hash'] = h.hexdigest()
    if update_info:
        update_info(info)
    _add_info_dir(t, tmp_dir, files, has_prefix, info)
    t.close()
    shutil.rmtree(tmp_dir)
    return warnings


def make_tarbz2(prefix, name='unknown', version='0.0', build_number=0,
                files=None):
    if files is None:
        files = untracked(prefix)
    print("# files: %d" % len(files))
    if len(files) == 0:
        print("# failed: nothing to do")
        return None

    if any('/site-packages/' in f for f in files):
        python_version = get_installed_version(prefix, 'python')
        assert python_version is not None
        requires_py = tuple(int(x) for x in python_version[:3].split('.'))
    else:
        requires_py = False

    info = create_info(name, version, build_number, requires_py)
    tarbz2_fn = '%(name)s-%(version)s-%(build)s.tar.bz2' % info
    create_conda_pkg(prefix, files, info, tarbz2_fn)
    print('# success')
    print(tarbz2_fn)
    return tarbz2_fn


def which_package(path):
    """
    given the path (of a (presumably) conda installed file) iterate over
    the conda packages the file came from.  Usually the iteration yields
    only one package.
    """
    path = abspath(path)
    prefix = which_prefix(path)
    if prefix is None:
        raise RuntimeError("could not determine conda prefix from: %s" % path)
    for dist in linked(prefix):
        meta = is_linked(prefix, dist)
        if any(abspath(join(prefix, f)) == path for f in meta['files']):
            yield dist


def which_prefix(path):
    """
    given the path (to a (presumably) conda installed file) return the
    environment prefix in which the file in located
    """
    prefix = abspath(path)
    while True:
        if isdir(join(prefix, 'conda-meta')):
            # we found the it, so let's return it
            return prefix
        if prefix == dirname(prefix):
            # we cannot chop off any more directories, so we didn't find it
            return None
        prefix = dirname(prefix)
