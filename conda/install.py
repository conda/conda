"""
This module contains:
  * all low-level code for extracting, activating and deactivating packages
  * a very simple CLI

The API functions are:
  - extract
  - activate
  - deactivate

These API functions  have argument names referring to:

    dist:        canonical package name (e.g. 'numpy-1.6.2-py26_0')

    pkgs_dir:    the "packages directory" (e.g. '/opt/anaconda/pkgs')

    prefix:      the prefix of a particular environment, which may also
                 be the "default" environment (i.e. sys.prefix),
                 but is otherwise something like '/opt/anaconda/envs/foo',
                 or even any prefix, e.g. '/home/joe/myenv'

Also, this module is directly invoked by the (self extracting (sfx)) tarball
installer to create the initial environment, therefore it needs to be
standalone, i.e. not import any other parts of conda (only depend of
the standard library).
"""

import os
import json
import shutil
import stat
import sys
import tarfile
import logging
from os.path import isdir, isfile, islink, join


log = logging.getLogger(__name__)


can_hard_link = True # bool(sys.platform != 'win32')


def rm_rf(path):
    if islink(path) or isfile(path):
        # Note that we have to check if the destination is a link because
        # exists('/path/to/dead-link') will return False, although
        # islink('/path/to/dead-link') is True.
        os.unlink(path)

    elif isdir(path):
        shutil.rmtree(path)


def yield_lines(path):
    for line in open(path):
        line = line.strip()
        if not line or line.startswith('#'):
            continue
        yield line


def update_prefix(path, new_prefix):
    with open(path) as fi:
        data = fi.read()
    new_data = data.replace('/opt/anaconda1anaconda2'
                            # the build prefix is intentionally split into
                            # parts, such that running this program on itself
                            # will leave it unchanged
                            'anaconda3', new_prefix)
    if new_data == data:
        return
    st = os.stat(path)
    os.unlink(path)
    with open(path, 'w') as fo:
        fo.write(new_data)
    os.chmod(path, stat.S_IMODE(st.st_mode))


def create_conda_meta(prefix, dist, info_dir, files):
    """
    Create the conda metadata, in a given prefix, for a given package.
    """
    meta_dir = join(prefix, 'conda-meta')
    with open(join(info_dir, 'index.json')) as fi:
        meta = json.load(fi)
    meta['files'] = files
    if not isdir(meta_dir):
        os.mkdir(meta_dir)
    with open(join(meta_dir, dist + '.json'), 'w') as fo:
        json.dump(meta, fo, indent=2, sort_keys=True)


# ========================== begin API functions =========================

def extract(pkgs_dir, dist, cleanup=False):
    '''
    Extract a package tarball into the conda packages directory, making
    it available.  We assume that the compressed packages is located in the
    packages directory.
    '''
    bz2path = join(pkgs_dir, dist + '.tar.bz2')
    assert isfile(bz2path), bz2path
    if not can_hard_link:
        return
    t = tarfile.open(bz2path)
    t.extractall(path=join(pkgs_dir, dist))
    t.close()
    if cleanup:
        os.unlink(bz2path)


def activate(pkgs_dir, dist, prefix):
    '''
    Set up a packages in a specified (environment) prefix.  We assume that
    the packages has been extracted (using extract() above).
    '''
    if can_hard_link:
        dist_dir = join(pkgs_dir, dist)
        info_dir = join(dist_dir, 'info')
        files = list(yield_lines(join(info_dir, 'files')))
        for f in files:
            src = join(dist_dir, f)
            fdn, fbn = os.path.split(f)
            dst_dir = join(prefix, fdn)
            if not isdir(dst_dir):
                os.makedirs(dst_dir)
            dst = join(dst_dir, fbn)
            if os.path.exists(dst):
                log.warn("file already exists: '%s'" % dst)
            else:
                try:
                    os.link(src, dst)
                except OSError:
                    log.error('failed to link (src=%r, dst=%r)' % (src, dst))

    else: # cannot hard link files
        info_dir = join(prefix, 'info')
        rm_rf(info_dir)
        t = tarfile.open(join(pkgs_dir, dist + '.tar.bz2'))
        t.extractall(path=prefix)
        t.close()
        files = list(yield_lines(join(info_dir, 'files')))        

    for f in yield_lines(join(info_dir, 'has_prefix')):
        update_prefix(join(prefix, f), prefix)

    create_conda_meta(prefix, dist, info_dir, files)
        


def deactivate(pkgs_dir, dist, prefix):
    '''
    Tear down a package, in the specified environment.
    '''
    dist_path = join(pkgs_dir, dist)
    dst_dirs = set()
    for f in yield_lines(join(dist_path, 'info/files')):
        fdn, fbn = os.path.split(f)
        dst_dir = join(prefix, fdn)
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

# =========================== end API functions ==========================

def main():
    prefix = sys.argv[1]
    pkgs_dir = join(prefix, 'pkgs')

    for dist in sorted(os.listdir(pkgs_dir)):
        activate(pkgs_dir, dist, prefix)


if __name__ == '__main__':
    main()
