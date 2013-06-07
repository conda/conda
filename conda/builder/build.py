import re
import os
import sys
import json
import tarfile
from subprocess import check_call
from os.path import abspath, exists, isdir, islink, join

import conda.config as cc
import conda.plan as plan
from conda.api import get_index

import config
from conda.fetch import fetch_index
import environ
import source
import tarcheck
from scripts import create_entry_points
from metadata import MetaData
from post import post_process, post_build, is_obj
from utils import rm_rf
from index import update_index
from create_test import create_test_files


prefix = config.build_prefix
info_dir = join(prefix, 'info')

bldpkgs_dir = join(config.croot, cc.subdir)


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

def create_info_files(m, files):
    os.mkdir(info_dir)

    with open(join(info_dir, 'files'), 'w') as fo:
        for f in files:
            if sys.platform == 'win32':
                f = f.replace('\\', '/')
            fo.write(f + '\n')

    with open(join(info_dir, 'index.json'), 'w') as fo:
        json.dump(m.info_index(), fo, indent=2, sort_keys=True)

    if sys.platform != 'win32':
        prefix_files = list(have_prefix_files(files))
        if prefix_files:
            with open(join(info_dir, 'has_prefix'), 'w') as fo:
                for f in prefix_files:
                    fo.write(f + '\n')

    with open(join(info_dir, 'meta'), 'w') as fo:
        fo.write('dist: %s\n' % m.dist_name())
        fo.write('has_bin: %s\n' % any(f.startswith('bin/') for f in files))
        p = re.compile(r'lib/[^/]+\.so')
        fo.write('has_lib: %s\n' % any(p.match(f) for f in files))
        p = re.compile(r'lib/python\d\.\d/site-packages/.+\.(so|py)')
        fo.write('has_py: %s\n' % any(p.match(f) for f in files))

    if m.get_value('source/git_url'):
        with open(join(info_dir, 'git'), 'w') as fo:
            source.git_info(fo)


def create_env(pref, specs):
    if not isdir(bldpkgs_dir):
        os.mkdir(bldpkgs_dir)
    update_index(bldpkgs_dir)
    fetch_index.cache = {}
    index = get_index(['file://%s' % config.croot])

    actions = plan.install_actions(pref, index, specs)
    plan.display_actions(actions, index)
    plan.execute_actions(actions, index, verbose=True)


def bldpkg_path(m):
    return join(bldpkgs_dir, '%s.tar.bz2' % m.dist_name())


def build(m, get_src=True):
    rm_rf(prefix)
    create_env(prefix, [ms.spec for ms in m.ms_depends('build')])

    print "BUILD START:", m.dist_name()

    if get_src:
        source.provide(m.path)
    assert isdir(source.WORK_DIR)
    print "source tree in:", source.get_dir()

    rm_rf(info_dir)
    files1 = prefix_files()

    if sys.platform == 'win32':
        import windows
        windows.build(m)
    else:
        env = environ.get_dict()
        cmd = ['/bin/bash', '-x', join(m.path, 'build.sh')]
        check_call(cmd, env=env, cwd=source.get_dir())
    create_entry_points(m.get_value('build/entry_points'))
    post_process()

    assert not exists(info_dir)
    files2 = prefix_files()

    sorted_files = sorted(files2 - files1)
    post_build(sorted_files)
    create_info_files(m, sorted_files)
    files3 = prefix_files()

    print "info/:"
    for f in sorted(files3 - files2):
        print '    %s' % f

    path = bldpkg_path(m)
    t = tarfile.open(path, 'w:bz2')
    for f in sorted(files3 - files1):
        t.add(join(prefix, f), f)
    t.close()

    print "BUILD END:", m.dist_name()

    # we're done building, perform some checks
    tarcheck.check_all(path)
    update_index(bldpkgs_dir)
    test(m)


def test(m):
    tmp_dir = join(config.croot, 'test-tmp_dir')
    rm_rf(tmp_dir)
    os.mkdir(tmp_dir)
    if not create_test_files(tmp_dir, m):
        print "Nothing to test for:", m.dist_name()
        return

    print "TEST START:", m.dist_name()

    rm_rf(config.test_prefix)
    specs = ['%s %s %s' % (m.name(), m.version(), m.build_id()),
             # as the tests are run by python, we need to specify it
             'python %s*' % environ.py_ver]
    # add packages listed in test/requires
    for spec in m.get_value('test/requires'):
        specs.append(spec)

    print specs
    create_env(config.test_prefix, specs)

    env = dict(os.environ)
    if sys.platform == 'win32':
        env['PATH'] = config.test_prefix + r'\Scripts;' + env['PATH']
    for varname in 'ANA_PY', 'ANA_NPY':
        env[varname] = str(getattr(config, varname))

    check_call([config.test_python, join(tmp_dir, 'run_test.py')],
               env=env, cwd=tmp_dir)

    print "TEST END:", m.dist_name()


def main():
    from optparse import OptionParser

    p = OptionParser(usage="usage: %prog [options] RECIPE",
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
