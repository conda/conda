"""
Handle the planning of installs and their execution.

NOTE:
    conda.install uses canonical package names in its interface functions,
    whereas conda.resolve uses package filenames, as those are used as index
    keys.  We try to keep fixes to this "impedance mismatch" local to this
    module.
"""

from __future__ import print_function, division, absolute_import

import re
import sys
from logging import getLogger
from collections import defaultdict
from os.path import abspath, isfile, join, exists

from conda import config
from conda import install
from conda.fetch import fetch_pkg
from conda.history import History
from conda.resolve import MatchSpec, Resolve
from conda.utils import md5_file, human_bytes

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
SYMLINK_CONDA = 'SYMLINK_CONDA'

progress_cmds = set([EXTRACT, RM_EXTRACTED, LINK, UNLINK])

def print_dists(dists_extras):
    fmt = "    %-27s|%17s"
    print(fmt % ('package', 'build'))
    print(fmt % ('-' * 27, '-' * 17))
    for dist, extra in dists_extras:
        line = fmt % tuple(dist.rsplit('-', 1))
        if extra:
            line += extra
        print(line)

def split_linkarg(arg):
    "Return tuple(dist, pkgs_dir, linktype)"
    pat = re.compile(r'\s*(\S+)(?:\s+(.+?)\s+(\d+))?\s*$')
    m = pat.match(arg)
    dist, pkgs_dir, linktype = m.groups()
    if pkgs_dir is None:
        pkgs_dir = config.pkgs_dirs[0]
    if linktype is None:
        linktype = install.LINK_HARD
    return dist, pkgs_dir, int(linktype)

def display_actions(actions, index=None):
    if actions.get(FETCH):
        print("\nThe following packages will be downloaded:\n")

        disp_lst = []
        for dist in actions[FETCH]:
            info = index[dist + '.tar.bz2']
            extra = '%15s' % human_bytes(info['size'])
            if config.show_channel_urls:
                extra += '  %s' % config.canonical_channel_name(
                                       info.get('channel'))
            disp_lst.append((dist, extra))
        print_dists(disp_lst)

        if index and len(actions[FETCH]) > 1:
            print(' ' * 4 + '-' * 60)
            print(" " * 43 + "Total: %14s" %
                  human_bytes(sum(index[dist + '.tar.bz2']['size']
                                  for dist in actions[FETCH])))
    if actions.get(UNLINK):
        print("\nThe following packages will be UN-linked:\n")
        print_dists([
                (dist, None)
                for dist in actions[UNLINK]])
    if actions.get(LINK):
        print("\nThe following packages will be linked:\n")
        lst = []
        for arg in actions[LINK]:
            dist, pkgs_dir, lt = split_linkarg(arg)
            extra = '   %s' % install.link_name_map.get(lt)
            lst.append((dist, extra))
        print_dists(lst)
    print()

# the order matters here, don't change it
action_codes = FETCH, EXTRACT, UNLINK, LINK, SYMLINK_CONDA, RM_EXTRACTED, RM_FETCHED

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
        if op in progress_cmds:
            res.append('PROGRESS %d' % len(actions[op]))
        for arg in actions[op]:
            res.append('%s %s' % (op, arg))
    return res

def extracted_where(dist):
    for pkgs_dir in config.pkgs_dirs:
        if install.is_extracted(pkgs_dir, dist):
            return pkgs_dir
    return None

def ensure_linked_actions(dists, prefix):
    actions = defaultdict(list)
    actions[PREFIX] = prefix
    for dist in dists:
        if install.is_linked(prefix, dist):
            continue

        extracted_in = extracted_where(dist)
        if extracted_in:
            if install.try_hard_link(extracted_in, prefix, dist):
                lt = install.LINK_HARD
            else:
                lt = (install.LINK_SOFT if (config.allow_softlinks and
                                            sys.platform != 'win32') else
                      install.LINK_COPY)
            actions[LINK].append('%s %s %d' % (dist, extracted_in, lt))
            continue

        actions[LINK].append(dist)
        actions[EXTRACT].append(dist)
        if install.is_fetched(config.pkgs_dirs[0], dist):
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
        pkg_path = join(config.pkgs_dirs[0], fn)
        if isfile(pkg_path):
            try:
                if md5_file(pkg_path) != index[fn]['md5']:
                    actions[RM_FETCHED].append(dist)
                    actions[FETCH].append(dist)
            except KeyError:
                sys.stderr.write('Warning: cannot lookup MD5 of: %s' % fn)
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
    # TODO: This should use the pinning mechanism. But don't change the API:
    # cas uses it.
    if r.explicit(specs):
        return
    log.debug('H0 specs=%r' % specs)
    names_linked = {install.name_dist(dist): dist for dist in linked}
    names_ms = {MatchSpec(s).name: MatchSpec(s) for s in specs}

    for name, def_ver in [('python', config.default_python),]:
                         #('numpy', config.default_numpy)]:
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
            # if Python/Numpy is already linked, we add that instead of the
            # default
            log.debug('H3 %s' % name)
            specs.append(dist2spec3v(names_linked[name]))
            continue

        if (name, def_ver) in [('python', '3.3'), ('python', '3.4')]:
            # Don't include Python 3 in the specs if this is the Python 3
            # version of conda.
            continue

        specs.append('%s %s*' % (name, def_ver))
    log.debug('HF specs=%r' % specs)

def get_pinned_specs(prefix):
    pinfile = join(prefix, 'conda-meta', 'pinned')
    if not exists(pinfile):
        return []
    with open(pinfile) as f:
        return list(filter(len, f.read().strip().split('\n')))

def install_actions(prefix, index, specs, force=False, only_names=None, pinned=True, minimal_hint=False):
    r = Resolve(index)
    linked = install.linked(prefix)

    if config.self_update and is_root_prefix(prefix):
        specs.append('conda')
    add_defaults_to_specs(r, linked, specs)
    if pinned:
        pinned_specs = get_pinned_specs(prefix)
        specs += pinned_specs
        # TODO: Improve error messages here

    must_have = {}
    for fn in r.solve(specs, [d + '.tar.bz2' for d in linked],
                      config.track_features, minimal_hint=minimal_hint):
        dist = fn[:-8]
        name = install.name_dist(dist)
        if only_names and name not in only_names:
            continue
        must_have[name] = dist

    if is_root_prefix(prefix):
        if install.on_win:
            for name in install.win_ignore_root:
                if name in must_have:
                    del must_have[name]
        for name in config.foreign:
            if name in must_have:
                del must_have[name]
    else:
        # discard conda from other environments
        if 'conda' in must_have:
            sys.exit("Error: 'conda' can only be installed into "
                     "root environment")

    smh = sorted(must_have.values())
    if force:
        actions = force_linked_actions(smh, index, prefix)
    else:
        actions = ensure_linked_actions(smh, prefix)

    if actions[LINK] and sys.platform != 'win32':
        actions[SYMLINK_CONDA] = [config.root_dir]

    for dist in sorted(linked):
        name = install.name_dist(dist)
        if name in must_have and dist != must_have[name]:
            actions[UNLINK].append(dist)

    return actions


def remove_actions(prefix, specs, pinned=True):
    linked = install.linked(prefix)

    mss = [MatchSpec(spec) for spec in specs]

    pinned_specs = get_pinned_specs(prefix)

    actions = defaultdict(list)
    actions[PREFIX] = prefix
    for dist in sorted(linked):
        if any(ms.match('%s.tar.bz2' % dist) for ms in mss):
            if pinned and any(MatchSpec(spec).match('%s.tar.bz2' % dist) for spec in
    pinned_specs):
                raise RuntimeError("Cannot remove %s because it is pinned. Use --no-pin to override." % dist)
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


def revert_actions(prefix, revision=-1):
    h = History(prefix)
    h.update()
    try:
        state = h.get_state(revision)
    except IndexError:
        sys.exit("Error: no such revision: %d" % revision)

    curr = h.get_state()
    if state == curr:
        return {}

    actions = ensure_linked_actions(state, prefix)
    for dist in curr - state:
        actions[UNLINK].append(dist)

    return actions

# ---------------------------- EXECUTION --------------------------

def fetch(index, dist):
    assert index is not None
    fn = dist + '.tar.bz2'
    fetch_pkg(index[fn])

def link(prefix, arg, index=None):
    dist, pkgs_dir, lt = split_linkarg(arg)
    install.link(pkgs_dir, prefix, dist, lt, index=index)

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
        from conda.console import setup_verbose_handlers
        setup_verbose_handlers()

    # set default prefix
    prefix = config.root_dir
    i = None
    cmds = cmds_from_plan(plan)

    for cmd, arg in cmds:
        if i is not None and cmd in progress_cmds:
            i += 1
            getLogger('progress.update').info((install.name_dist(arg), i))

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
            install.extract(config.pkgs_dirs[0], arg)
        elif cmd == RM_EXTRACTED:
            install.rm_extracted(config.pkgs_dirs[0], arg)
        elif cmd == RM_FETCHED:
            install.rm_fetched(config.pkgs_dirs[0], arg)
        elif cmd == LINK:
            link(prefix, arg, index=index)
        elif cmd == UNLINK:
            install.unlink(prefix, arg)
        elif cmd == SYMLINK_CONDA:
            install.symlink_conda(prefix, arg)
        else:
            raise Exception("Did not expect command: %r" % cmd)

        if i is not None and cmd in progress_cmds and maxval == i:
            i = None
            getLogger('progress.stop').info(None)

    install.messages(prefix)


def execute_actions(actions, index=None, verbose=False):
    plan = plan_from_actions(actions)
    with History(actions[PREFIX]):
        execute_plan(plan, index, verbose)


if __name__ == '__main__':
    # for testing new revert_actions() only
    from pprint import pprint
    pprint(dict(revert_actions(sys.prefix, int(sys.argv[1]))))
