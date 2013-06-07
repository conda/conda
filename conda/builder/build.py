import re
import os
import sys
import json
import tarfile
from subprocess import check_call
from os.path import (abspath, basename, exists, isdir, isfile,
                     islink, join)

import config
import environ
import source
import tarcheck
from scripts import create_entry_points
from metadata import MetaData
from post import post_process, post_build, is_obj

from utils import bzip2, bunzip2, rm_rf, tar_xf


prefix = config.build_prefix
info_dir = join(prefix, 'info')


def tar_pkg_path(pkg):
    return join(config.TARS_DIR, dist_name(pkg) + '.tar')


def mkdir_prefix():
    rm_rf(prefix)
    assert not exists(prefix)
    os.mkdir(prefix)


def prefix_files():
    res = set()
    for root, dirs, files in os.walk(prefix):
        for fn in files:
            res.add(join(root, fn)[len(prefix) + 1:])
        for dn in dirs:
            path = join(root, dn)
            if islink(path):
                res.add(path[len(prefix) + 1:])
    return res


def have_prefix_files(files):
    for f in files:
        if f.endswith(('.pyc', '.pyo', '.a')):
            continue
        path = join(prefix, f)
        if isdir(path):
            continue
        if sys.platform != 'darwin' and islink(path):
            # OSX does not allow hard-linking symbolic links, so we cannot
            # skip symbolic links (as we can on Linux)
            continue
        if is_obj(path):
            continue
        with open(path) as fi:
            data = fi.read()
        if prefix in data:
            yield f

def create_info_files(pkg, files):
    os.mkdir(info_dir)

    with open(join(info_dir, 'files'), 'w') as fo:
        for f in files:
            if sys.platform == 'win32':
                f = f.replace('\\', '/')
            fo.write(f + '\n')

    with open(join(info_dir, 'requires'), 'w') as fo:
        print 'run_requires:'
        for p in sorted(run_requires(pkg)):
            d = dist_name(p)
            print '    %s' % d
            fo.write(d + '\n')

    with open(join(info_dir, 'index.json'), 'w') as fo:
        json.dump(info_index(pkg), fo, indent=2, sort_keys=True)

    if sys.platform != 'win32':
        prefix_files = list(have_prefix_files(files))
        if prefix_files:
            with open(join(info_dir, 'has_prefix'), 'w') as fo:
                for f in prefix_files:
                    fo.write(f + '\n')

    with open(join(info_dir, 'meta'), 'w') as fo:
        fo.write('pkg: %s\n' % pkg)
        fo.write('dist: %s\n' % dist_name(pkg))
        for field in 'about/home', 'about/license':
            fo.write('%s: %s\n' % (field.split('/')[1],
                                   get_meta_value(pkg, field)))
        fo.write('has_bin: %s\n' % any(f.startswith('bin/') for f in files))
        p = re.compile(r'lib/[^/]+\.so')
        fo.write('has_lib: %s\n' % any(p.match(f) for f in files))
        p = re.compile(r'lib/python\d\.\d/site-packages/.+\.(so|py)')
        fo.write('has_py: %s\n' % any(p.match(f) for f in files))

    if get_meta_value(pkg, 'source/git_url'):
        with open(join(info_dir, 'git'), 'w') as fo:
            source.git_info(fo)


def available(pkg):
    if isfile(tar_pkg_path(pkg)):
        return True

    fn = dist_name(pkg) + '.tar.bz2'
    return check_pkg(config.REPOS, fn, verbose=True)


def install(pkg):
    # assumes that packge is available, i.e. available(pkg) is True
    assert available(pkg), pkg
    if not isfile(tar_pkg_path(pkg)):
        fn = dist_name(pkg) + '.tar.bz2'
        assert fetch_pkg(config.REPOS, fn, config.TARS_DIR, verbose=True)
        bunzip2(join(config.TARS_DIR, fn), verbose=True)

    path = tar_pkg_path(pkg)
    assert isfile(path)
    print "installing:", basename(path)
    tar_xf(path, prefix)


def build(pkg, deps=True, get_src=True, only_build=False):
    if deps:
        for p in build_requires(pkg):
            if available(p):
                continue
            build(p)

    print "BUILD START:", dist_name(pkg)

    if config.PRO == 2:
        assert get_meta_value(pkg, 'build/channel') == 'w'

    if get_src:
        source.provide(pkg)
    assert isdir(source.WORK_DIR)
    print "source tree in:", source.get_dir()

    mkdir_prefix()
    if deps and not is_meta_pkg(pkg):
        for p in build_requires(pkg):
            install(p)
    rm_rf(info_dir)
    files1 = prefix_files()

    if sys.platform == 'win32':
        import windows
        windows.build(pkg)
    else:
        env = environ.get_dict(pkg)
        cmd = ['/bin/bash', '-x', join(env['PKG_PATH'], 'build.sh')]
        check_call(cmd, env=env, cwd=source.get_dir())
    create_entry_points(get_meta_value(pkg, 'build/entry_points'))
    post_process(pkg)

    assert not exists(info_dir)
    files2 = prefix_files()

    sorted_files = sorted(files2 - files1)
    post_build(pkg, sorted_files)
    create_info_files(pkg, sorted_files)
    files3 = prefix_files()

    print "info/:"
    for f in sorted(files3 - files2):
        print '    %s' % f

    if not isdir(config.TARS_DIR):
        os.mkdir(config.TARS_DIR)

    path = tar_pkg_path(pkg)
    t = tarfile.open(path, 'w')
    for f in sorted(files3 - files1):
        t.add(join(prefix, f), f)
    t.close()

    # we're done building, perform some checks and upload to filer
    print "tarball build: %s" % basename(path)
    tarcheck.check_all(path)
    print "BUILD END:", dist_name(pkg)

    if only_build:
        return

    if deps:
        for p in run_requires(pkg):
            if available(p):
                continue
            build(p)

    test(pkg)
    bzip2(path)


def test(pkg):
    tmp_dir = join(AROOT, 'test-tmp_dir')
    rm_rf(tmp_dir)
    os.mkdir(tmp_dir)
    if not create_test_files(tmp_dir, pkg):
        print "Nothing to test for:", pkg
        return

    print "TEST START:", dist_name(pkg)

    packages = run_requires(pkg, include_self=True)
    # as the tests are run by python, they require it
    packages.add(find('python'))
    # add packages listed in test/require
    for name in get_meta_value(pkg, 'test/requires'):
        packages.add(find(name))

    mkdir_prefix()
    for p in sorted(packages):
        install(p)

    env = dict(os.environ)
    if sys.platform == 'win32':
        env['PATH'] = config.test_prefix + r'\Scripts;' + env['PATH']
    for varname in 'ANA_PY', 'ANA_NPY':
        env[varname] = str(getattr(config, varname))

    check_call([config.PYTHON, join(tmp_dir, 'run_test.py')],
               env=env, cwd=tmp_dir)

    print "TEST END:", dist_name(pkg)


def main():
    from optparse import OptionParser

    p = OptionParser(usage="usage: %prog [options] PACKAGE [PACKAGE ...]",
                     description="build a package")
    p.add_option('--clean',
                 action='store_true',
                 help="clean WORK_DIR before doing anything else")
    p.add_option('--no-patch',
                 action='store_true',
                 help="don't apply any source patches (only works with -s)")
    p.add_option('-s', '--source',
                 action='store_true',
                 help='only obtain the (patched) source')
    p.add_option('-S', '--skip-source',
                 action='store_true',
                 help='do not obtain source, just build (the opposite of -s)')
    p.add_option('-t', '--test',
                 action='store_true',
                 help='test a package')
    opts, args = p.parse_args()

    print "-------------------------------------"
    config.show()
    print "-------------------------------------"

    if opts.source and opts.skip_source:
        p.error('--source and --skip-source exclude each other')

    if opts.clean:
        print "Removing:", source.WORK_DIR
        rm_rf(source.WORK_DIR)

    for arg in args:
        path = abspath(arg)
        m = MetaData(path)

        if opts.test:
            test(m)
        elif opts.source:
            source.provide(m.path, patch=not opts.no_patch)
            print 'Source tree in:', source.get_dir()
        else:
            build(m, get_src=not opts.skip_source)


if __name__ == '__main__':
    main()
