# this module contains miscellaneous stuff which enventually could be moved
# into other places

from __future__ import print_function, division, absolute_import

import os
import sys
import shutil
import subprocess
from collections import defaultdict
from distutils.spawn import find_executable
from os.path import abspath, basename, expanduser, join

import config
import install
from plan import RM_EXTRACTED, EXTRACT, UNLINK, LINK, execute_actions



def install_local_packages(prefix, paths, verbose=False):
    # copy packages to pkgs dir
    dists = []
    for src_path in paths:
        assert src_path.endswith('.tar.bz2')
        fn = basename(src_path)
        dists.append(fn[:-8])
        dst_path = join(config.pkgs_dir, fn)
        if abspath(src_path) == abspath(dst_path):
            continue
        shutil.copyfile(src_path, dst_path)

    actions = defaultdict(list)
    actions['PREFIX'] = prefix
    actions['op_order'] = RM_EXTRACTED, EXTRACT, UNLINK, LINK
    for dist in dists:
        actions[RM_EXTRACTED].append(dist)
        actions[EXTRACT].append(dist)
        if install.is_linked(prefix, dist):
            actions[UNLINK].append(dist)
        actions[LINK].append(dist)
    execute_actions(actions, verbose=verbose)


def launch(fn, prefix=config.root_dir, additional_args=None):
    info = install.is_linked(prefix, fn[:-8])
    if info is None:
        return None

    if not info.get('type') == 'app':
        raise Exception('Not an application: %s' % fn)

    # prepend the bin directory to the path
    fmt = r'%s\Scripts;%s' if sys.platform == 'win32' else '%s/bin:%s'
    env = {'PATH': fmt % (abspath(prefix), os.getenv('PATH'))}
    # copy existing environment variables, but not anything with PATH in it
    for k, v in os.environ.iteritems():
        if 'PATH' not in k:
            env[k] = v
    # allow updating environment variables from metadata
    if 'app_env' in info:
        env.update(info['app_env'])

    # call the entry command
    args = info['app_entry'].split()
    args = [a.replace('${PREFIX}', prefix) for a in args]
    arg0 = find_executable(args[0], env['PATH'])
    if arg0 is None:
        raise Exception('Executable not found: %s' % args[0])
    args[0] = arg0

    cwd = abspath(expanduser('~'))
    if additional_args:
        args.extend(additional_args)
    return subprocess.Popen(args, cwd=cwd , env=env)


if __name__ == '__main__':
    from optparse import OptionParser

    p = OptionParser(usage="usage: %prog [options] DIST/FN [ADDITIONAL ARGS]")
    p.add_option('-p', '--prefix',
                 action="store",
                 default=sys.prefix,
                 help="prefix (defaults to %default)")
    opts, args = p.parse_args()

    if len(args) == 0:
        p.error('at least one argument expected')

    fn = args[0]
    if not fn.endswith('.tar.bz2'):
        fn += '.tar.bz2'
    p = launch(fn, opts.prefix, args[1:])
    print 'PID:', p.pid
