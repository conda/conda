# this module contains miscellaneous stuff which enventually could be moved
# into other places
import os
import sys
import json
import shutil
from subprocess import check_call
from collections import defaultdict
from os.path import abspath, basename, join

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


def launch(app_dir):
    with open(join(app_dir, 'meta.json')) as fi:
        meta = json.load(fi)
    # prepend the bin directory to the path
    fmt = r'%s\Scripts;%s' if sys.platform == 'win32' else '%s/bin:%s'
    env = {'PATH': fmt % (abspath(join(app_dir, '..', '..')),
                          os.getenv('PATH'))}
    # copy existing environment variables, but not anything with PATH in it
    for k, v in os.environ.iteritems():
        if 'PATH' not in k:
            env[k] = v
    # allow updating environment variables from metadata
    if 'env' in meta:
        env.update(meta['env'])
    # call the entry command
    check_call(meta['entry'].split(), cwd=app_dir, env=env)


if __name__ == '__main__':
    launch('/Users/ilan/python/App/filebin')
