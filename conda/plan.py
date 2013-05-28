"""
Handle the planning of installs and their execution.

NOTE:
    conda.install uses canonical package names in its interface functions,
    whereas conda.resolve uses package filenames, as those are used as index
    keys.  We try to keep fixes to this "impedance mismatch" local to this
    module.
"""
import sys
from collections import defaultdict

import install
import config
from remote import fetch_file
from resolve import MatchSpec, Resolve
from progressbar import Bar, ETA, FileTransferSpeed, Percentage, ProgressBar



def name_dist(dist):
    return dist.rsplit('-', 2)[0]


def print_dists(dists):
    fmt = "    %-27s|%17s"
    print fmt % ('package', 'build')
    print fmt % ('-' * 27, '-' * 17)
    for dist in dists:
        print fmt % tuple(dist.rsplit('-', 1))

def display_actions(actions):
    if actions.get('FETCH'):
        print "\nThe following packages will be downloaded:\n"
        print_dists(actions['FETCH'])
    if actions.get('UNLINK'):
        print "\nThe following packages will be UN-linked:\n"
        print_dists(actions['UNLINK'])
    if actions.get('LINK'):
        print "\nThe following packages will be linked:\n"
        print_dists(actions['LINK'])
    print

def nothing_to_do(actions):
    for op in ('FETCH', 'EXTRACT', 'UNLINK', 'LINK',
               'RM_EXTRACTED', 'RM_FETCHED'):
        if actions.get(op):
            return False
    return True

def plan_from_actions(actions):
    res = ['# plan',
           'PREFIX %s' % actions['PREFIX']]
    for op in ('FETCH', 'EXTRACT', 'UNLINK', 'LINK',
               'RM_EXTRACTED', 'RM_FETCHED'):
        if op not in actions:
            continue
        if not actions[op]:
            continue
        res.append('PRINT %sing packages ...' % op.capitalize())
        if op not in ('FETCH', 'RM_FETCHED'):
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
        actions['LINK'].append(dist)
        if dist in extracted:
            continue
        actions['EXTRACT'].append(dist)
        if dist in fetched:
            continue
        actions['FETCH'].append(dist)
    return actions

def dist2spec(fn):
    name, version, unused = fn.rsplit('-', 2)
    return '%s %s*' % (name, version[:3])

def add_defaults_to_specs(r, linked, specs):
    names_linked = {name_dist(fn): fn for fn in linked}
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

def install_actions(prefix, index, specs):
    r = Resolve(index)
    linked = install.linked(prefix)
    add_defaults_to_specs(r, linked, specs)

    must_have = {}
    for fn in r.solve(specs, [d + '.tar.bz2' for d in linked], verbose=1):
        dist = fn[:-8]
        must_have[name_dist(dist)] = dist

    # discard conda from environments (other than the root environment)
    if prefix != config.root_dir and 'conda' in must_have:
        del must_have['conda']

    actions = ensure_linked_actions(sorted(must_have.values()), linked)
    actions['PREFIX'] = prefix

    for dist in sorted(linked):
        name = name_dist(dist)
        if name in must_have and dist != must_have[name]:
            actions['UNLINK'].append(dist)

    return actions

def remove_all_actions(prefix):
    assert prefix != config.root_dir
    linked = install.linked(prefix)

    return {'PREFIX': prefix,
            'UNLINK': sorted(linked)}

def remove_actions(prefix, specs):
    linked = install.linked(prefix)

    mss = [MatchSpec(spec) for spec in specs]

    actions = defaultdict(list)
    actions['PREFIX'] = prefix
    for dist in sorted(linked):
        if any(ms.match('%s.tar.bz2' % dist) for ms in mss):
            actions['UNLINK'].append(dist)

    return actions

def remove_features_actions(prefix, index, features):
    linked = install.linked(prefix)
    r = Resolve(index)

    actions = defaultdict(list)
    actions['PREFIX'] = prefix
    _linked = [d + '.tar.bz2' for d in linked]
    to_link = []
    for dist in sorted(linked):
        fn = dist + '.tar.bz2'
        if fn not in index:
            continue
        if r.track_features(fn).intersection(features):
            actions['UNLINK'].append(dist)
        if r.features(fn).intersection(features):
            actions['UNLINK'].append(dist)
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
    info = index[fn]
    fetch_file(info['channel'], fn, md5=info['md5'], size=info['size'],
               progress=progress)

def cmds_from_plan(plan):
    res = []
    for line in plan:
        line = line.strip()
        if not line or line.startswith('#'):
            continue
        res.append(line.split(None, 1))
    return res

def execute_plan(plan, index=None, enable_progress=True):
    if enable_progress:
        fetch_progress = ProgressBar(
            widgets=['', ' ', Percentage(), ' ', Bar(), ' ', ETA(), ' ',
                     FileTransferSpeed()])
        progress = ProgressBar(
            widgets=['', ' ', Bar(), ' ', Percentage()])
    else:
        fetch_progress = None
        progress = None

    progress_cmds = set(['EXTRACT', 'RM_EXTRACTED', 'LINK', 'UNLINK'])
    prefix = config.root_dir
    i = None
    for cmd, arg in cmds_from_plan(plan):
        if i is not None and cmd in progress_cmds:
            i += 1
            progress.widgets[0] = '[%-20s]' % name_dist(arg)
            progress.update(i)

        if cmd == 'PREFIX':
            prefix = arg
        elif cmd == 'PRINT':
            print arg
        elif cmd == 'FETCH':
            fetch(index, arg, fetch_progress)
        elif cmd == 'PROGRESS':
            if enable_progress:
                i = 0
                progress.maxval = int(arg)
                progress.start()
        elif cmd == 'EXTRACT':
            install.extract(config.pkgs_dir, arg)
        elif cmd == 'RM_EXTRACTED':
            install.rm_extracted(config.pkgs_dir, arg)
        elif cmd == 'LINK':
            install.link(config.pkgs_dir, arg, prefix)
        elif cmd == 'UNLINK':
            install.unlink(arg, prefix)
        else:
            raise Exception("Did not expect command: %r" % cmd)

        if i is not None and cmd in progress_cmds and progress.maxval == i:
            i = None
            progress.widgets[0] = '[      COMPLETE      ]'
            progress.finish()

def execute_actions(actions, index=None, enable_progress=True):
    plan = plan_from_actions(actions)
    execute_plan(plan, index, enable_progress)


if __name__ == '__main__':
    import json
    with open('../tests/index.json') as fi:
        index = json.load(fi)
    #actions = install_actions(sys.prefix, index, ['starcluster'])
    actions = remove_features_actions(sys.prefix, index, ['mkl'])
    #for line in plan_from_actions(actions):
    #    print line
    display_actions(actions)
