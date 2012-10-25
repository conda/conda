import os
import subprocess
import logging
from os.path import isdir, isfile, join

from sfx import yield_lines, sfx_activate


log = logging.getLogger(__name__)


def extract(pkg, env, cleanup=False):
    '''
    extract a package tarball into the conda packages directory, making
    it available
    '''
    dirpath = join(env.conda.packages_dir, pkg.canonical_name)
    bz2path = join(env.conda.packages_dir, pkg.filename)
    assert isfile(bz2path), bz2path
    if not isdir(dirpath):
        os.mkdir(dirpath)
    subprocess.check_call(['tar', 'xjf', bz2path], cwd=dirpath)
    if cleanup:
        os.unlink(bz2path)


def activate(pkg, env):
    '''
    set up link farm for the specified package, in the specified Anaconda
    environment
    '''
    sfx_activate(env.conda.packages_dir, pkg.canonical_name, env.prefix)


def deactivate(pkg, env):
    '''
    tear down link farm for the specified package, in the specified
    Anaconda environment
    '''
    dist_path = join(env.conda.packages_dir, pkg.canonical_name)
    dst_dirs = set()
    for f in yield_lines(join(dist_path, 'info/files')):
        fdn, fbn = os.path.split(f)
        dst_dir = join(env.prefix, fdn)
        dst_dirs.add(dst_dir)
        dst = join(dst_dir, fbn)
        try:
            os.unlink(dst)
        except OSError: # file might not exist
            log.debug("could not remove file: '%s'" % dst)

    for path in sorted(dst_dirs, key=len, reverse=True):
        try:
            os.rmdir(path)
        except OSError: # directory might not exist or not be empty
            log.debug("could not remove directory: '%s'" % dst)

