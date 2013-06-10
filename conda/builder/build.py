import os
import sys
import json
import shutil
import tarfile
from subprocess import check_call
from os.path import exists, isdir, islink, join

import conda.config as cc
import conda.plan as plan
from conda.api import get_index
from conda.install import prefix_placeholder

import config
from conda.fetch import fetch_index
import environ
import source
import tarcheck
from scripts import create_entry_points
from post import post_process, post_build, is_obj, fix_permissions
from utils import rm_rf, url_path
from index import update_index
from create_test import create_test_files


prefix = config.build_prefix
info_dir = join(prefix, 'info')

bldpkgs_dir = join(config.croot, cc.subdir)


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
        if prefix_placeholder in data:
            yield f

def create_info_files(m, files):
    os.makedirs(info_dir)

    shutil.copytree(m.path, join(info_dir, 'recipe'))

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

    if m.get_value('source/git_url'):
        with open(join(info_dir, 'git'), 'w') as fo:
            source.git_info(fo)

    if m.get_value('app/icon'):
        shutil.copyfile(join(m.path, m.get_value('app/icon')),
                        join(info_dir, 'icon.png'))


def create_env(pref, specs):
    if not isdir(bldpkgs_dir):
        os.makedirs(bldpkgs_dir)
    update_index(bldpkgs_dir)
    fetch_index.cache = {}
    index = get_index([url_path(config.croot)])

    actions = plan.install_actions(pref, index, specs)
    plan.display_actions(actions, index)
    plan.execute_actions(actions, index, verbose=True)

def rm_pkgs_cache(dist):
    rmplan = ['RM_FETCHED %s' % dist,
              'RM_EXTRACTED %s' % dist]
    plan.execute_plan(rmplan)

def bldpkg_path(m):
    return join(bldpkgs_dir, '%s.tar.bz2' % m.dist())


def build(m, get_src=True):
    rm_rf(prefix)
    create_env(prefix, [ms.spec for ms in m.ms_depends('build')])

    print "BUILD START:", m.dist()

    if get_src:
        source.provide(m.path, m.get_section('source'))
    assert isdir(source.WORK_DIR)
    print "source tree in:", source.get_dir()

    rm_rf(info_dir)
    files1 = prefix_files()

    if sys.platform == 'win32':
        import windows
        windows.build(m.path)
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
    fix_permissions()

    path = bldpkg_path(m)
    t = tarfile.open(path, 'w:bz2')
    for f in sorted(files3 - files1):
        t.add(join(prefix, f), f)
    t.close()

    print "BUILD END:", m.dist()

    # we're done building, perform some checks
    tarcheck.check_all(path)
    update_index(bldpkgs_dir)
    # remove from packages, because we're going to test it
    rm_pkgs_cache(m.dist())
    test(m)


def test(m):
    tmp_dir = join(config.croot, 'test-tmp_dir')
    rm_rf(tmp_dir)
    rm_rf(prefix)
    os.makedirs(tmp_dir)
    if not create_test_files(tmp_dir, m):
        print "Nothing to test for:", m.dist()
        return

    print "TEST START:", m.dist()

    rm_rf(config.test_prefix)
    specs = ['%s %s %s' % (m.name(), m.version(), m.build_id()),
             # as the tests are run by python, we need to specify it
             'python %s*' % environ.py_ver]
    # add packages listed in test/requires
    for spec in m.get_value('test/requires'):
        specs.append(spec)

    create_env(config.test_prefix, specs)

    env = dict(os.environ)
    if sys.platform == 'win32':
        env['PATH'] = config.test_prefix + r'\Scripts;' + env['PATH']
    for varname in 'ANA_PY', 'ANA_NPY':
        env[varname] = str(getattr(config, varname))

    check_call([config.test_python, join(tmp_dir, 'run_test.py')],
               env=env, cwd=tmp_dir)

    print "TEST END:", m.dist()
