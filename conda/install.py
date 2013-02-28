# (c) 2012-2013 Continuum Analytics, Inc. / http://continuum.io
# All Rights Reserved
#
# conda is distributed under the terms of the BSD 3-clause license.
# Consult LICENSE.txt or http://opensource.org/licenses/BSD-3-Clause.
''' This module contains:
  * all low-level code for extracting, linking and unlinking packages
  * a very simple CLI

These API functions have argument names referring to:

    dist:        canonical package name (e.g. 'numpy-1.6.2-py26_0')

    pkgs_dir:    the "packages directory" (e.g. '/opt/anaconda/pkgs')

    prefix:      the prefix of a particular environment, which may also
                 be the "default" environment (i.e. sys.prefix),
                 but is otherwise something like '/opt/anaconda/envs/foo',
                 or even any prefix, e.g. '/home/joe/myenv'

Also, this module is directly invoked by the (self extracting (sfx)) tarball
installer to create the initial environment, therefore it needs to be
standalone, i.e. not import any other parts of `conda` (only depend on
the standard library).

'''
import os
import json
import shutil
import stat
import sys
import tarfile
import traceback
import logging
from os.path import abspath, basename, dirname, isdir, isfile, islink, join


log = logging.getLogger(__name__)


use_hard_links = bool(sys.platform != 'win32')


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


prefix_placeholder = ('/opt/anaconda1anaconda2'
                      # this is intentionally split into parts,
                      # such that running this program on itself
                      # will leave it unchanged
                      'anaconda3')
def update_prefix(path, new_prefix):
    with open(path) as fi:
        data = fi.read()
    new_data = data.replace(prefix_placeholder, new_prefix)
    if new_data == data:
        return
    st = os.stat(path)
    os.unlink(path)
    with open(path, 'w') as fo:
        fo.write(new_data)
    os.chmod(path, stat.S_IMODE(st.st_mode))


def create_meta(prefix, dist, info_dir, files):
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


def mk_menus(prefix, files, remove=False):
    if abspath(prefix) != abspath(sys.prefix):
        # we currently only want to create menu items for packages
        # in default environment
        return
    menu_files = [f for f in files
                  if f.startswith('Menu/') and f.endswith('.json')]
    if not menu_files:
        return
    try:
        import menuinst
    except ImportError:
        return
    for f in menu_files:
        try:
            menuinst.install(join(prefix, f), remove, prefix)
        except:
            print("Appinst Exception:")
            traceback.print_exc(file=sys.stdout)


# ========================== begin API functions =========================

# ------- things about available packages

def available(pkgs_dir):
    """
    Return the (set of canonical names) of all available packages.
    """
    if use_hard_links:
        return set(fn for fn in os.listdir(pkgs_dir)
                   if isdir(join(pkgs_dir, fn)))
    else:
        return set(fn[:-8] for fn in os.listdir(pkgs_dir)
                   if fn.endswith('.tar.bz2'))


def make_available(pkgs_dir, dist, cleanup=False):
    '''
    Make a package available for linkage.  We assume that the
    compressed packages is located in the packages directory.
    '''
    bz2path = join(pkgs_dir, dist + '.tar.bz2')
    assert isfile(bz2path), bz2path
    if not use_hard_links:
        return
    t = tarfile.open(bz2path)
    t.extractall(path=join(pkgs_dir, dist))
    t.close()
    if cleanup:
        os.unlink(bz2path)


def remove_available(pkgs_dir, dist):
    '''
    Remove a package from the packages directory.
    '''
    bz2path = join(pkgs_dir, dist + '.tar.bz2')
    rm_rf(bz2path)
    if use_hard_links:
        rm_rf(join(pkgs_dir, dist))

# ------- things about linkage of packages

def linked(prefix):
    """
    Return the (set of canonical names) of linked packages in prefix.
    """
    meta_dir = join(prefix, 'conda-meta')
    if not isdir(meta_dir):
        return set()
    return set(fn[:-5] for fn in os.listdir(meta_dir) if fn.endswith('.json'))


def get_meta(dist, prefix):
    """
    Return the install meta-data for a linked package in a prefix, or None
    if the package is not linked in the prefix.
    """
    meta_path = join(prefix, 'conda-meta', dist + '.json')
    try:
        with open(meta_path) as fi:
            return json.load(fi)
    except OSError:
        return None


def link(pkgs_dir, dist, prefix):
    '''
    Set up a packages in a specified (environment) prefix.  We assume that
    the packages has been make available (using make_available() above).
    '''
    if use_hard_links:
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
                log.warn("file already exists: %r" % dst)
                try:
                    os.unlink(dst)
                except OSError:
                    log.error('failed to unlink: %r' % dst)
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

    has_prefix_path = join(info_dir, 'has_prefix')
    if isfile(has_prefix_path):
        for f in yield_lines(has_prefix_path):
            update_prefix(join(prefix, f), prefix)

    create_meta(prefix, dist, info_dir, files)
    mk_menus(prefix, files, remove=False)


def unlink(dist, prefix):
    '''
    Remove a package from the specified environment, it is an error of the
    package does not exist in the prefix.
    '''
    meta_path = join(prefix, 'conda-meta', dist + '.json')
    with open(meta_path) as fi:
        meta = json.load(fi)

    mk_menus(prefix, meta['files'], remove=True)
    dst_dirs = set()
    for f in meta['files']:
        dst = join(prefix, f)
        dst_dirs.add(dirname(dst))
        try:
            os.unlink(dst)
        except OSError: # file might not exist
            log.debug("could not remove file: '%s'" % dst)

    for path in sorted(dst_dirs, key=len, reverse=True):
        try:
            os.rmdir(path)
        except OSError: # directory might not exist or not be empty
            log.debug("could not remove directory: '%s'" % dst)

    os.unlink(meta_path)

# =========================== end API functions ==========================

def install_local_package(path, pkgs_dir, prefix):
    assert path.endswith('.tar.bz2')
    dist = basename(path)[:-8]
    print '%s:' % dist
    if dist in available(pkgs_dir):
        print "    already available - removing"
        remove_available(pkgs_dir, dist)
    shutil.copyfile(path, join(pkgs_dir, dist + '.tar.bz2'))
    print "    making available"
    make_available(pkgs_dir, dist)
    if dist in linked(prefix):
        print "    already linked - unlinking"
        unlink(dist, prefix)
    print "    linking"
    link(pkgs_dir, dist, prefix)


def main():
    from pprint import pprint
    from optparse import OptionParser

    p = OptionParser(
        usage="usage: %prog [options] [TARBALL/NAME]",
        description="low-level conda install tool, by default extracts "
                    "(if necessary) and links a TARBALL")

    p.add_option('-l', '--list',
                 action="store_true",
                 help="list all linked packages")

    p.add_option('--list-available',
                 action="store_true",
                 help="list all available packages")

    p.add_option('-i', '--info',
                 action="store_true",
                 help="display meta-data information of a linked package")

    p.add_option('-m', '--make-available',
                 action="store_true",
                 help="make a package available (when we use hard like this "
                      "means extracting it)")

    p.add_option('--link',
                 action="store_true",
                 help="link a package")

    p.add_option('--unlink',
                 action="store_true",
                 help="unlink a package")

    p.add_option('-r', '--remove',
                 action="store_true",
                 help="remove a package (from being available)")

    p.add_option('-p', '--prefix',
                 action="store",
                 default=sys.prefix,
                 help="prefix (defaults to %default)")

    p.add_option('--pkgs-dir',
                 action="store",
                 default=join(sys.prefix, 'pkgs'),
                 help="packages directory (defaults to %default)")

    p.add_option('--link-all',
                 action="store_true",
                 help="link all available (extracted) packages")

    p.add_option('-v', '--verbose',
                 action="store_true")

    opts, args = p.parse_args()

    logging.basicConfig()

    if opts.list or opts.list_available or opts.link_all:
        if args:
            p.error('no arguments expected')
    else:
        if len(args) == 1:
            dist = basename(args[0])
            if dist.endswith('.tar.bz2'):
                dist = dist[:-8]
        else:
            p.error('exactly one argument expected')

    if opts.verbose:
        print "pkgs_dir: %r" % opts.pkgs_dir
        print "prefix  : %r" % opts.prefix
        print "dist    : %r" % dist

    if opts.list:
        pprint(sorted(linked(opts.prefix)))
        return

    if opts.list_available:
        pprint(sorted(available(opts.pkgs_dir)))
        return

    if opts.info:
        pprint(get_meta(dist, opts.prefix))
        return

    if opts.link_all:
        for d in sorted(available(opts.pkgs_dir)):
            link(opts.pkgs_dir, d, opts.prefix)
        return

    do_steps = not (opts.remove or opts.make_available or opts.link or
                    opts.unlink)
    if opts.verbose:
        print "do_steps: %r" % do_steps

    if do_steps:
        path = args[0]
        if not (path.endswith('.tar.bz2') and isfile(path)):
            p.error('path .tar.bz2 package expected')

    if do_steps or opts.remove:
        if opts.verbose:
            print "removing available package: %r" % dist
        remove_available(opts.pkgs_dir, dist)

    if do_steps:
        shutil.copyfile(path, join(opts.pkgs_dir, dist + '.tar.bz2'))

    if do_steps or opts.make_available:
        if opts.verbose:
            print "making available: %r" % dist
        make_available(opts.pkgs_dir, dist)

    if (do_steps and dist in linked(opts.prefix)) or opts.unlink:
        if opts.verbose:
            print "unlinking: %r" % dist
        unlink(dist, opts.prefix)

    if do_steps or opts.link:
        if opts.verbose:
            print "linking: %r" % dist
        link(opts.pkgs_dir, dist, opts.prefix)


if __name__ == '__main__':
    main()
