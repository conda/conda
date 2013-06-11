"""
Handle the planning of installs and their execution.

NOTE:
    conda.install uses canonical package names in its interface functions,
    whereas conda.resolve uses package filenames, as those are used as index
    keys.  We try to keep fixes to this "impedance mismatch" local to this
    module.
"""
from logging import getLogger

from collections import defaultdict
from os.path import abspath, isfile, join

import config
import install
from naming import name_dist
from utils import md5_file, human_bytes
from fetch import fetch_pkg
from resolve import MatchSpec, Resolve

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
    print fmt % ('package', 'build')
    print fmt % ('-' * 27, '-' * 17)
    for dist in dists:
        line = fmt % tuple(dist.rsplit('-', 1))
        fn = dist + '.tar.bz2'
        if index and fn in index:
            line += '%15s' % human_bytes(index[fn]['size'])
        print line

def display_actions(actions, index=None):
    if actions.get(FETCH):
        print "\nThe following packages will be downloaded:\n"
        print_dists(actions[FETCH], index)
    if actions.get(UNLINK):
        print "\nThe following packages will be UN-linked:\n"
        print_dists(actions[UNLINK])
    if actions.get(LINK):
        print "\nThe following packages will be linked:\n"
        print_dists(actions[LINK])
    print


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
            log.debug('H1 %s' % name)
            continue

        if (not any(any(any(ms.name == name for ms in r.ms_depends(fn))
                        for fn in r.get_max_dists(MatchSpec(spec)))
                    for spec in specs)
            and
                name not in names_ms):
            log.debug('H2 %s' % name)
            continue

        if name in names_linked:
            log.debug('H3 %s' % name)
            specs.append(dist2spec3v(names_linked[name]))
            continue

        specs.append('%s %s*' % (name, def_ver))


def install_actions(prefix, index, specs, force=False, only_names=None):
    r = Resolve(index)
    linked = install.linked(prefix)

    if is_root_prefix(prefix):
        specs.append('conda')
    add_defaults_to_specs(r, linked, specs)

    must_have = {}
    for fn in r.solve(specs, [d + '.tar.bz2' for d in linked]):
        dist = fn[:-8]
        name = name_dist(dist)
        if only_names and name not in only_names:
            continue
        must_have[name] = dist

    if is_root_prefix(prefix):
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

    actions[PREFIX] = prefix

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
        from console import setup_handlers
        setup_handlers()

    progress_cmds = set([EXTRACT, RM_EXTRACTED, LINK, UNLINK])
    prefix = config.root_dir
    i = None
    for cmd, arg in cmds_from_plan(plan):
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
        else:
            raise Exception("Did not expect command: %r" % cmd)

        if i is not None and cmd in progress_cmds and maxval == i:
            i = None
            getLogger('progress.stop').info(None)


def execute_actions(actions, index=None, verbose=False):
    plan = plan_from_actions(actions)
    execute_plan(plan, index, verbose)
