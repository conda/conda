"""
Handle the planning of installs and their execution.

NOTE:
    conda.install uses canonical package names in its interface functions,
    whereas conda.resolve uses package filenames, as those are used as index
    keys.  We try to keep fixes to this "impedance mismatch" local to this
    module.
"""
from collections import defaultdict
from os.path import isfile, join

import install
import config
from utils import md5_file, human_bytes
from fetch import fetch_pkg
from resolve import MatchSpec, Resolve
from progressbar import Bar, ETA, FileTransferSpeed, Percentage, ProgressBar


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


def name_dist(dist):
    return dist.rsplit('-', 2)[0]


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


def ensure_linked_actions(dists, linked):
    extracted = install.extracted(config.pkgs_dir)
    fetched = install.fetched(config.pkgs_dir)

    actions = defaultdict(list)
    for dist in dists:
        if dist in linked:
            continue
        actions[LINK].append(dist)
        if dist in extracted:
            continue
        actions[EXTRACT].append(dist)
        if dist in fetched:
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


def dist2spec(dist):
    name, version, unused_build = dist.rsplit('-', 2)
    return '%s %s*' % (name, version[:3])

def add_defaults_to_specs(r, linked, specs):
    names_linked = {name_dist(dist): dist for dist in linked}
    names_spec = set(MatchSpec(s).name for s in specs)
    for name, def_ver in [('python', config.default_python),
                          ('numpy', config.default_numpy)]:
        if name in names_spec:
            continue
        if not any(any(any(ms.name == name for ms in r.ms_depends(fn))
                       for fn in r.get_max_dists(MatchSpec(spec)))
                   for spec in specs):
            continue
        if name in names_linked:
            specs.append(dist2spec(names_linked[name]))
            continue
        specs.append('%s %s*' % (name, def_ver))


def install_actions(prefix, index, specs, force=False, only_names=None):
    r = Resolve(index)
    linked = install.linked(prefix)
    add_defaults_to_specs(r, linked, specs)

    must_have = {}
    for fn in r.solve(specs, [d + '.tar.bz2' for d in linked]):
        dist = fn[:-8]
        name = name_dist(dist)
        if only_names and name not in only_names:
            continue
        must_have[name] = dist

    # discard conda from environments (other than the root environment)
    if prefix != config.root_dir and 'conda' in must_have:
        del must_have['conda']

    smh = sorted(must_have.values())
    if force:
        actions = force_linked_actions(smh, index, prefix)
    else:
        actions = ensure_linked_actions(smh, linked)

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
        actions.update(ensure_linked_actions(to_link, linked))
    return actions

# ---------------------------- EXECUTION --------------------------

def fetch(index, dist, progress):
    assert index is not None
    fn = dist + '.tar.bz2'
    fetch_pkg(index[fn], progress=progress)


def cmds_from_plan(plan):
    res = []
    for line in plan:
        line = line.strip()
        if not line or line.startswith('#'):
            continue
        res.append(line.split(None, 1))
    return res


def execute_plan(plan, index=None, verbose=False):
    if verbose:
        fetch_progress = ProgressBar(
            widgets=['', ' ', Percentage(), ' ', Bar(), ' ', ETA(), ' ',
                     FileTransferSpeed()])
        progress = ProgressBar(
            widgets=['', ' ', Bar(), ' ', Percentage()])
    else:
        fetch_progress = None
        progress = None

    progress_cmds = set([EXTRACT, RM_EXTRACTED, LINK, UNLINK])
    prefix = config.root_dir
    i = None
    for cmd, arg in cmds_from_plan(plan):
        if i is not None and cmd in progress_cmds:
            i += 1
            progress.widgets[0] = '[%-20s]' % name_dist(arg)
            progress.update(i)

        if cmd == PREFIX:
            prefix = arg
        elif cmd == PRINT:
            if verbose:
                print arg
        elif cmd == FETCH:
            fetch(index, arg, fetch_progress)
        elif cmd == PROGRESS:
            if verbose:
                i = 0
                progress.maxval = int(arg)
                progress.start()
        elif cmd == EXTRACT:
            install.extract(config.pkgs_dir, arg)
        elif cmd == RM_EXTRACTED:
            install.rm_extracted(config.pkgs_dir, arg)
        elif cmd == LINK:
            install.link(config.pkgs_dir, arg, prefix)
        elif cmd == UNLINK:
            install.unlink(arg, prefix)
        else:
            raise Exception("Did not expect command: %r" % cmd)

        if i is not None and cmd in progress_cmds and progress.maxval == i:
            i = None
            progress.widgets[0] = '[      COMPLETE      ]'
            progress.finish()


def execute_actions(actions, index=None, verbose=False):
    plan = plan_from_actions(actions)
    execute_plan(plan, index, verbose)
