from collections import defaultdict

import install
from config import ROOT_DIR, PKGS_DIR
from naming import name_dist
from remote import fetch_file
from resolve import MatchSpec, Resolve
from progressbar import Bar, ETA, FileTransferSpeed, Percentage, ProgressBar



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
        if not actions[op]:
            continue
        res.append('PRINT %sing packages ...' % op.capitalize())
        if op not in ('FETCH', 'RM_FETCHED'):
            res.append('PROGRESS %d' % len(actions[op]))
        for dist in actions[op]:
            res.append('%s %s' % (op, dist))
    return res

def arg2spec(arg):
    spec = arg.replace('=', ' ')
    if arg.count('=') == 1:
        spec += '*'
    return spec

def install_actions(prefix, index, args):
    linked = install.linked(prefix)
    extracted = install.extracted(PKGS_DIR)
    fetched = install.fetched(PKGS_DIR)

    r = Resolve(index)

    must_have = {}
    for fn in r.solve([arg2spec(arg) for arg in args],
                      ['%s.tar.bz2' % d for d in linked]):
        dist = fn[:-8]
        must_have[name_dist(dist)] = dist
    sorted_must_have = sorted(must_have.values())

    actions = defaultdict(list)
    actions['PREFIX'] = prefix
    for dist in sorted_must_have:
        if dist in linked:
            continue
        actions['LINK'].append(dist)
        if dist in extracted:
            continue
        actions['EXTRACT'].append(dist)
        if dist in fetched:
            continue
        actions['FETCH'].append(dist)

    for dist in sorted(linked):
        name = name_dist(dist)
        if name in must_have and dist != must_have[name]:
            actions['UNLINK'].append(dist)

    return actions

def remove_actions(prefix, args):
    linked = install.linked(prefix)

    mss = [MatchSpec(arg2spec(arg)) for arg in args]

    actions = defaultdict(list)
    actions['PREFIX'] = prefix
    for dist in sorted(linked):
        if any(ms.match('%s.tar.bz2' % dist) for ms in mss):
            actions['UNLINK'].append(dist)

    return actions

# ---------------------------- EXECUTION --------------------------

def fetch(index, dist, progress):
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
    prefix = ROOT_DIR
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
            fetch(index or {}, arg, fetch_progress)
        elif cmd == 'PROGRESS':
            if enable_progress:
                i = 0
                progress.maxval = int(arg)
                progress.start()
        elif cmd == 'EXTRACT':
            install.extract(PKGS_DIR, arg)
        elif cmd == 'RM_EXTRACTED':
            install.rm_extracted(PKGS_DIR, arg)
        elif cmd == 'LINK':
            install.link(PKGS_DIR, arg, prefix)
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
    import sys
    import json
    with open('../tests/index.json') as fi:
        index = json.load(fi)
    actions = install_actions(sys.prefix, index, ['w3lib'])
    for line in plan_from_actions(actions):
        print line
