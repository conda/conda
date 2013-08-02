"""
Handle the planning of installs and their execution.

NOTE:
    conda.install uses canonical package names in its interface functions,
    whereas conda.resolve uses package filenames, as those are used as index
    keys.  We try to keep fixes to this "impedance mismatch" local to this
    module.
"""

from __future__ import print_function, division, absolute_import

import sys
import os
from logging import getLogger
from collections import defaultdict
from os.path import abspath, isfile, join, dirname

from conda import config
from conda import install
from conda.naming import name_dist
from conda.utils import md5_file, human_bytes
from conda.fetch import fetch_pkg
from conda.resolve import MatchSpec, Resolve

log = getLogger(__name__)


# op codes
FETCH = 'FETCH'
EXTRACT = 'EXTRACT'
UNLINK = 'UNLINK'
LINK = 'LINK'
RM_EXTRACTED = 'RM_EXTRACTED'
RM_FETCHED = 'RM_FETCHED'
PREFIX = 'PREFIX'
PRINT = 'PRINT'
PROGRESS = 'PROGRESS'



def print_dists(dists, index=None):
    fmt = "    %-27s|%17s"
    print(fmt % ('package', 'build'))
    print(fmt % ('-' * 27, '-' * 17))
    for dist in dists:
        line = fmt % tuple(dist.rsplit('-', 1))
        fn = dist + '.tar.bz2'
        if index and fn in index:
            line += '%15s' % human_bytes(index[fn]['size'])
        print(line)

def display_actions(actions, index=None):
    if actions.get(FETCH):
        print("\nThe following packages will be downloaded:\n")
        print_dists(actions[FETCH], index)
    if actions.get(UNLINK):
        print("\nThe following packages will be UN-linked:\n")
        print_dists(actions[UNLINK])
    if actions.get(LINK):
        print("\nThe following packages will be linked:\n")
        print_dists(actions[LINK])
    print()


# the order matters here, don't change it
action_codes = FETCH, EXTRACT, UNLINK, LINK, RM_EXTRACTED, RM_FETCHED

def nothing_to_do(actions):
    for op in action_codes:
        if actions.get(op):
            return False
    return True

def plan_from_actions(actions):
    if 'op_order' in actions and actions['op_order']:
        op_order = actions['op_order']
    else:
        op_order = action_codes

    assert PREFIX in actions and actions[PREFIX]
    res = ['# plan',
           'PREFIX %s' % actions[PREFIX]]
    for op in op_order:
        if op not in actions:
            continue
        if not actions[op]:
            continue
        if '_' not in op:
            res.append('PRINT %sing packages ...' % op.capitalize())
        if op not in (FETCH, RM_FETCHED, RM_EXTRACTED):
            res.append('PROGRESS %d' % len(actions[op]))
        for dist in actions[op]:
            res.append('%s %s' % (op, dist))
    return res


def ensure_linked_actions(dists, prefix):
    actions = defaultdict(list)
    actions[PREFIX] = prefix
    for dist in dists:
        if install.is_linked(prefix, dist):
            continue
        actions[LINK].append(dist)
        if install.is_extracted(config.pkgs_dir, dist):
            continue
        actions[EXTRACT].append(dist)
        if install.is_fetched(config.pkgs_dir, dist):
            continue
        actions[FETCH].append(dist)
    return actions


def force_linked_actions(dists, index, prefix):
    actions = defaultdict(list)
    actions[PREFIX] = prefix
    actions['op_order'] = (RM_FETCHED, FETCH, RM_EXTRACTED, EXTRACT,
                           UNLINK, LINK)
    for dist in dists:
        fn = dist + '.tar.bz2'
        pkg_path = join(config.pkgs_dir, fn)
        if isfile(pkg_path):
            if md5_file(pkg_path) != index[fn]['md5']:
                actions[RM_FETCHED].append(dist)
                actions[FETCH].append(dist)
        else:
            actions[FETCH].append(dist)
        actions[RM_EXTRACTED].append(dist)
        actions[EXTRACT].append(dist)
        if isfile(join(prefix, 'conda-meta', dist + '.json')):
            actions[UNLINK].append(dist)
        actions[LINK].append(dist)
    return actions

# -------------------------------------------------------------------

def is_root_prefix(prefix):
    return abspath(prefix) == abspath(config.root_dir)

def dist2spec3v(dist):
    name, version, unused_build = dist.rsplit('-', 2)
    return '%s %s*' % (name, version[:3])

def add_defaults_to_specs(r, linked, specs):
    if r.explicit(specs):
        return
    log.debug('H0 specs=%r' % specs)
    names_linked = {name_dist(dist): dist for dist in linked}
    names_ms = {MatchSpec(s).name: MatchSpec(s) for s in specs}

    for name, def_ver in [('python', config.default_python),
                          ('numpy', config.default_numpy)]:
        ms = names_ms.get(name)
        if ms and ms.strictness > 1:
            # if any of the specifications mention the Python/Numpy version,
            # we don't need to add the default spec
            log.debug('H1 %s' % name)
            continue

        any_depends_on = any(ms2.name == name
                             for spec in specs
                             for fn in r.get_max_dists(MatchSpec(spec))
                             for ms2 in r.ms_depends(fn))
        log.debug('H2 %s %s' % (name, any_depends_on))

        if not any_depends_on and name not in names_ms:
            # if nothing depends on Python/Numpy AND the Python/Numpy is not
            # specified, we don't need to add the default spec
            log.debug('H2A %s' % name)
            continue

        if (any_depends_on and len(specs) >= 1 and
                  MatchSpec(specs[0]).strictness == 3):
            # if something depends on Python/Numpy, but the spec is very
            # explicit, we also don't need to add the default spec
            log.debug('H2B %s' % name)
            continue

        if name in names_linked:
            # if Python/Numpy is already linked, we also don't need to add
            # the default
            log.debug('H3 %s' % name)
            specs.append(dist2spec3v(names_linked[name]))
            continue

        specs.append('%s %s*' % (name, def_ver))
    log.debug('HF specs=%r' % specs)


def install_actions(prefix, index, specs, force=False, only_names=None):
    r = Resolve(index)
    linked = install.linked(prefix)

    # Here is a temporary fix to prevent adding conda to the specs;
    # Bootstrapping problem: conda is not available as a conda package for
    # py3k yet.
    PY3 = sys.version_info[0] == 3

    if is_root_prefix(prefix) and not PY3:
        specs.append('conda')
    add_defaults_to_specs(r, linked, specs)

    must_have = {}
    for fn in r.solve(specs, [d + '.tar.bz2' for d in linked]):
        dist = fn[:-8]
        name = name_dist(dist)
        if only_names and name not in only_names:
            continue
        must_have[name] = dist

    if is_root_prefix(prefix) and not PY3:
        if not force:
            # ensure conda is in root environment
            assert 'conda' in must_have
    else:
        # discard conda from other environments
        if 'conda' in must_have:
            del must_have['conda']

    smh = sorted(must_have.values())
    if force:
        actions = force_linked_actions(smh, index, prefix)
    else:
        actions = ensure_linked_actions(smh, prefix)

    for dist in sorted(linked):
        name = name_dist(dist)
        if name in must_have and dist != must_have[name]:
            actions[UNLINK].append(dist)

    return actions


def remove_actions(prefix, specs):
    linked = install.linked(prefix)

    mss = [MatchSpec(spec) for spec in specs]

    actions = defaultdict(list)
    actions[PREFIX] = prefix
    for dist in sorted(linked):
        if any(ms.match('%s.tar.bz2' % dist) for ms in mss):
            actions[UNLINK].append(dist)

    return actions


def remove_features_actions(prefix, index, features):
    linked = install.linked(prefix)
    r = Resolve(index)

    actions = defaultdict(list)
    actions[PREFIX] = prefix
    _linked = [d + '.tar.bz2' for d in linked]
    to_link = []
    for dist in sorted(linked):
        fn = dist + '.tar.bz2'
        if fn not in index:
            continue
        if r.track_features(fn).intersection(features):
            actions[UNLINK].append(dist)
        if r.features(fn).intersection(features):
            actions[UNLINK].append(dist)
            subst = r.find_substitute(_linked, features, fn)
            if subst:
                to_link.append(subst[:-8])

    if to_link:
        actions.update(ensure_linked_actions(to_link, prefix))
    return actions

# ---------------------------- EXECUTION --------------------------

def fetch(index, dist):
    assert index is not None
    fn = dist + '.tar.bz2'
    fetch_pkg(index[fn])


def cmds_from_plan(plan):
    res = []
    for line in plan:
        log.debug(' %s' % line)
        line = line.strip()
        if not line or line.startswith('#'):
            continue
        res.append(line.split(None, 1))
    return res

def execute_plan(plan, index=None, verbose=False):
    if verbose:
        from conda.console import setup_handlers
        setup_handlers()

    progress_cmds = set([EXTRACT, RM_EXTRACTED, LINK, UNLINK])
    prefix = config.root_dir
    i = None
    cmds = cmds_from_plan(plan)

    if any(should_do_win_subprocess(cmd, arg, prefix) for (cmd, arg) in cmds):
        try:
            test_win_subprocess(prefix)
        except Exception as e:
            # If anything doesn't work, let's bail
            print("It failed")
            print(e)
            winplan = ''
            wincmds = []
        else:
            print("It succeeded")
            plan, winplan = win_subprocess_re_sort(plan, prefix)
            cmds, wincmds = cmds_from_plan(plan), cmds_from_plan(winplan)
    else:
        winplan = ''
        wincmds = []

    for cmd, arg in cmds:
        if i is not None and cmd in progress_cmds:
            i += 1
            getLogger('progress.update').info((name_dist(arg), i))

        if cmd == PREFIX:
            prefix = arg
        elif cmd == PRINT:
            getLogger('print').info(arg)
        elif cmd == FETCH:
            fetch(index, arg)
        elif cmd == PROGRESS:
            i = 0
            maxval = int(arg)
            getLogger('progress.start').info(maxval)
        elif cmd == EXTRACT:
            install.extract(config.pkgs_dir, arg)
        elif cmd == RM_EXTRACTED:
            install.rm_extracted(config.pkgs_dir, arg)
        elif cmd == RM_FETCHED:
            install.rm_fetched(config.pkgs_dir, arg)
        elif cmd == LINK:
            install.link(config.pkgs_dir, prefix, arg)
        elif cmd == UNLINK:
            install.unlink(prefix, arg)
        elif cmd == 'CREATEMETA':
            # We have to skip link() and use win_batlink in Windows, but this
            # is the one step from install.link() that is needed for those
            # packages that is not done there.
            assert sys.platform == 'win32'
            dist_dir = join(config.pkgs_dir, arg)
            info_dir = join(dist_dir, 'info')
            files = list(install.yield_lines(join(info_dir, 'files')))
            install.create_meta(prefix, arg, info_dir, files)
        else:
            raise Exception("Did not expect command: %r" % cmd)

        if i is not None and cmd in progress_cmds and maxval == i:
            i = None
            getLogger('progress.stop').info(None)


    # Wait for conda to exit
    # This is the portable way to sleep for 3 seconds. See
    # http://stackoverflow.com/a/1672349/161801
    batfiles = ['ping 1.1.1.1 -n 1 -w 3000 > nul']
    for cmd, arg in wincmds:
        batfiles.append(win_subprocess_write_bat(cmd, arg, prefix, plan))
    batfiles.append("""
echo done
echo.
""")
    if wincmds:
        batfile = '\n'.join(batfiles)
        do_win_subprocess(batfile, prefix)


def should_do_win_subprocess(cmd, arg, prefix):
    """
    If the cmd needs to call out to a separate process on Windows (because the
    Windows file lock prevents Python from updating itself).
    """
    return (
        cmd in ('LINK', 'UNLINK') and
        install.on_win and
        abspath(prefix) == abspath(sys.prefix) and
        arg.rsplit('-', 2)[0] in install.win_ignore
        )

def win_subprocess_re_sort(plan, prefix):
    # TODO: Fix the progress numbers
    newplan = []
    winplan = []
    for line in plan:
        cmd_arg = cmds_from_plan([line])
        if cmd_arg:
            [[cmd, arg]] = cmd_arg
        else:
            continue
        if should_do_win_subprocess(cmd, arg, prefix=prefix):
            if cmd == LINK:
                # The one post-link action that we need to worry about
                newplan.append("CREATEMETA %s" % arg)
            winplan.append(line)
        else:
            newplan.append(line)

    return newplan, winplan

def test_win_subprocess(prefix):
    """
    Make sure the windows subprocess stuff will work before we try it.
    """
    import subprocess
    from conda.win_batlink import make_bat_link, make_bat_unlink
    from conda.builder.utils import rm_rf

    try:
        print("Testing if we can install certain packages")
        batfiles = ['ping 1.1.1.1 -n 1 -w 3000 > nul']
        dist_dir = join(config.pkgs_dir, 'battest_pkg', 'battest')

        # First create a file in the prefix.
        print("making file in the prefix")
        prefix_battest = join(prefix, 'battest')
        print("making directories")
        os.makedirs(join(prefix, 'battest'))
        print("making file")
        with open(join(prefix_battest, 'battest1'), 'w') as f:
            f.write('test1')
        print("testing file")
        with open(join(prefix_battest, 'battest1')) as f:
            assert f.read() == 'test1'

        # Now unlink it.
        print("making unlink command")
        batfiles.append(make_bat_unlink([join(prefix_battest, 'battest1')],
        [prefix_battest], prefix, dist_dir))

        # Now create a file in the pkgs dir
        print("making file in pkgs dir")
        print("making directories")
        os.makedirs(join(dist_dir))
        print("making file")
        with open(join(dist_dir, 'battest2'), 'w') as f:
            f.write('test2')
        print("testing file")
        with open(join(dist_dir, 'battest2')) as f:
            assert f.read() == 'test2'

        # And link it
        print("making link command")
        batfiles.append(make_bat_link(['battest2'], prefix, dist_dir))

        batfile = '\n'.join(batfiles)

        print("writing batlink_test.bat file")
        with open(join(prefix, 'batlink_test.bat'), 'w') as f:
            f.write(batfile)
        print("running batlink_test.bat file")
        subprocess.check_call([join(prefix, 'batlink_test.bat')])

        print("testing result")
        assert not os.path.exists(join(prefix_battest, 'battest1'))
        assert os.path.exists(join(prefix_battest, 'battest2'))
        with open(join(prefix_battest, 'battest2')) as f:
            assert f.read() == 'test2'
        with open(join(dist_dir, 'battest2')) as f:
            assert f.read() == 'test2'

    finally:
        try:
            print("cleaning up")
            rm_rf(join(prefix, 'battest'))
            rm_rf(join(config.pkgs_dir, 'battest_pkg'))
            rm_rf(join(prefix, 'batlink_test.bat'))
        except Exception as e:
            print(e)

def win_subprocess_write_bat(cmd, arg, prefix, plan):
    assert sys.platform == 'win32'

    import json
    from conda.win_batlink import make_bat_link, make_bat_unlink

    dist_dir = join(config.pkgs_dir, arg)
    info_dir = join(dist_dir, 'info')

    if cmd == LINK:
        files = list(install.yield_lines(join(info_dir, 'files')))

        return make_bat_link(files, prefix, dist_dir)

    elif cmd == UNLINK: # cmd == "UNLINK"
        meta_path = join(prefix, 'conda-meta', arg + '.json')
        with open(meta_path) as fi:
            meta = json.load(fi)

        files = set([])
        directories1 = set([])
        for f in meta['files']:
            dst = abspath(join(prefix, f))
            files.add(dst)
            directories1.add(dirname(dst))
        files.add(meta_path)

        directories = set([])
        for path in directories1:
            while len(path) > len(prefix):
                directories.add(path)
                path = dirname(path)
        directories.add(join(prefix, 'conda-meta'))
        directories.add(prefix)

        directories = sorted(directories, key=len, reverse=True)

        return make_bat_unlink(files, directories, prefix, dist_dir)
    else:
        raise ValueError

def do_win_subprocess(batfile, prefix):
    import subprocess
    with open(join(prefix, 'batlink.bat'), 'w') as f:
        f.write(batfile)
    print("running subprocess")
    subprocess.Popen([join(prefix, 'batlink.bat')])
    # If we ever hit a race condition, maybe we should use atexit
    sys.exit(0)

def execute_actions(actions, index=None, verbose=False):
    plan = plan_from_actions(actions)
    execute_plan(plan, index, verbose)
