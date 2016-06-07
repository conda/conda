"""
Handle the planning of installs and their execution.

NOTE:
    conda.install uses canonical package names in its interface functions,
    whereas conda.resolve uses package filenames, as those are used as index
    keys.  We try to keep fixes to this "impedance mismatch" local to this
    module.
"""

from __future__ import print_function, division, absolute_import

import os
import sys
from collections import defaultdict
from logging import getLogger
from os.path import abspath, basename, dirname, join, exists

from conda import install
from conda import instructions as inst
from conda.config import (always_copy as config_always_copy, url_channel,
                          show_channel_urls as config_show_channel_urls,
                          root_dir, allow_softlinks, default_python, self_update,
                          track_features, foreign, canonical_channel_name)
from conda.exceptions import CondaException
from conda.history import History
from conda.resolve import MatchSpec, Resolve, Package
from conda.utils import md5_file, human_bytes
from conda.install import dist2quad

# For backwards compatibility

log = getLogger(__name__)

def print_dists(dists_extras):
    fmt = "    %-27s|%17s"
    print(fmt % ('package', 'build'))
    print(fmt % ('-' * 27, '-' * 17))
    for dist, extra in dists_extras:
        dist = dist2quad(dist)
        line = fmt % (dist[0]+'-'+dist[1], dist[2])
        if extra:
            line += extra
        print(line)


def display_actions(actions, index, show_channel_urls=None):
    if show_channel_urls is None:
        show_channel_urls = config_show_channel_urls

    def channel_str(rec):
        if 'schannel' in rec:
            return rec['schannel']
        if 'url' in rec:
            return url_channel(rec['url'])[1]
        if 'channel' in rec:
            return canonical_channel_name(rec['channel'])
        return '<unknown>'

    def channel_filt(s):
        if show_channel_urls is False:
            return ''
        if show_channel_urls is None and s == 'defaults':
            return ''
        return s

    if actions.get(inst.FETCH):
        print("\nThe following packages will be downloaded:\n")

        disp_lst = []
        for dist in actions[inst.FETCH]:
            info = index[dist + '.tar.bz2']
            extra = '%15s' % human_bytes(info['size'])
            schannel = channel_filt(channel_str(info))
            if schannel:
                extra += '  ' + schannel
            disp_lst.append((dist, extra))
        print_dists(disp_lst)

        if index and len(actions[inst.FETCH]) > 1:
            num_bytes = sum(index[dist + '.tar.bz2']['size']
                            for dist in actions[inst.FETCH])
            print(' ' * 4 + '-' * 60)
            print(" " * 43 + "Total: %14s" % human_bytes(num_bytes))

    # package -> [oldver-oldbuild, newver-newbuild]
    packages = defaultdict(lambda: list(('', '')))
    features = defaultdict(lambda: list(('', '')))
    channels = defaultdict(lambda: list(('', '')))
    records = defaultdict(lambda: list((None, None)))
    linktypes = {}

    for arg in actions.get(inst.LINK, []):
        dist, lt = inst.split_linkarg(arg)
        fkey = dist + '.tar.bz2'
        rec = index[fkey]
        pkg = rec['name']
        channels[pkg][1] = channel_str(rec)
        packages[pkg][1] = rec['version'] + '-' + rec['build']
        records[pkg][1] = Package(fkey, rec)
        linktypes[pkg] = lt
        features[pkg][1] = rec.get('features', '')
    for arg in actions.get(inst.UNLINK, []):
        dist, lt = inst.split_linkarg(arg)
        fkey = dist + '.tar.bz2'
        rec = index.get(fkey)
        if rec is None:
            pkg, ver, build, schannel = dist2quad(dist)
            rec = dict(name=pkg, version=ver, build=build, channel=None,
                       schannel='<unknown>',
                       build_number=int(build) if build.isdigit() else 0)
        pkg = rec['name']
        channels[pkg][0] = channel_str(rec)
        packages[pkg][0] = rec['version'] + '-' + rec['build']
        records[pkg][0] = Package(fkey, rec)
        features[pkg][0] = rec.get('features', '')

    #                     Put a minimum length here---.    .--For the :
    #                                                 v    v

    if packages:
        maxpkg = max(len(p) for p in packages) + 1
        maxoldver = max(len(p[0]) for p in packages.values())
        maxnewver = max(len(p[1]) for p in packages.values())
        maxoldfeatures = max(len(p[0]) for p in features.values())
        maxnewfeatures = max(len(p[1]) for p in features.values())
        maxoldchannels = max(len(channel_filt(p[0])) for p in channels.values())
        maxnewchannels = max(len(channel_filt(p[1])) for p in channels.values())
    new = {p for p in packages if not packages[p][0]}
    removed = {p for p in packages if not packages[p][1]}
    updated = set()
    downgraded = set()
    oldfmt = {}
    newfmt = {}
    for pkg in packages:
        # That's right. I'm using old-style string formatting to generate a
        # string with new-style string formatting.
        oldfmt[pkg] = '{pkg:<%s} {vers[0]:<%s}' % (maxpkg, maxoldver)
        if maxoldchannels:
            oldfmt[pkg] += ' {channels[0]:<%s}' % maxoldchannels
        if packages[pkg][0]:
            newfmt[pkg] = '{vers[1]:<%s}' % maxnewver
        else:
            newfmt[pkg] = '{pkg:<%s} {vers[1]:<%s}' % (maxpkg, maxnewver)
        if maxnewchannels:
            newfmt[pkg] += ' {channels[1]:<%s}' % maxnewchannels
        # TODO: Should we also care about the old package's link type?
        if pkg in linktypes and linktypes[pkg] != install.LINK_HARD:
            newfmt[pkg] += ' (%s)' % install.link_name_map[linktypes[pkg]]

        if features[pkg][0]:
            oldfmt[pkg] += ' [{features[0]:<%s}]' % maxoldfeatures
        if features[pkg][1]:
            newfmt[pkg] += ' [{features[1]:<%s}]' % maxnewfeatures

        if pkg in new or pkg in removed:
            continue
        P0 = records[pkg][0]
        P1 = records[pkg][1]
        try:
            # <= here means that unchanged packages will be put in updated
            newer = ((P0.name, P0.norm_version, P0.build_number) <=
                     (P1.name, P1.norm_version, P1.build_number))
        except TypeError:
            newer = ((P0.name, P0.version, P0.build_number) <=
                     (P1.name, P1.version, P1.build_number))
        if newer or str(P1.version) == 'custom':
            updated.add(pkg)
        else:
            downgraded.add(pkg)

    arrow = ' --> '
    lead = ' ' * 4

    def format(s, pkg):
        chans = [channel_filt(c) for c in channels[pkg]]
        return lead + s.format(pkg=pkg + ':', vers=packages[pkg],
                               channels=chans, features=features[pkg])

    if new:
        print("\nThe following NEW packages will be INSTALLED:\n")
    for pkg in sorted(new):
        print(format(newfmt[pkg], pkg))

    if removed:
        print("\nThe following packages will be REMOVED:\n")
    for pkg in sorted(removed):
        print(format(oldfmt[pkg], pkg))

    if updated:
        print("\nThe following packages will be UPDATED:\n")
    for pkg in sorted(updated):
        print(format(oldfmt[pkg] + arrow + newfmt[pkg], pkg))

    if downgraded:
        print("\nThe following packages will be DOWNGRADED:\n")
    for pkg in sorted(downgraded):
        print(format(oldfmt[pkg] + arrow + newfmt[pkg], pkg))

    print()


def nothing_to_do(actions):
    for op in inst.action_codes:
        if actions.get(op):
            return False
    return True


def add_unlink(actions, dist):
    if inst.UNLINK not in actions:
        actions[inst.UNLINK] = []
    actions[inst.UNLINK].append(dist)


def plan_from_actions(actions):
    if 'op_order' in actions and actions['op_order']:
        op_order = actions['op_order']
    else:
        op_order = inst.action_codes

    assert inst.PREFIX in actions and actions[inst.PREFIX]
    res = [('PREFIX', '%s' % actions[inst.PREFIX])]

    if sys.platform == 'win32':
        # Always link/unlink menuinst first on windows in case a subsequent
        # package tries to import it to create/remove a shortcut

        for op in (inst.UNLINK, inst.FETCH, inst.EXTRACT, inst.LINK):
            if op in actions:
                pkgs = []
                for pkg in actions[op]:
                    if 'menuinst' in pkg:
                        res.append((op, pkg))
                    else:
                        pkgs.append(pkg)
                actions[op] = pkgs

    for op in op_order:
        if op not in actions:
            continue
        if not actions[op]:
            continue
        if '_' not in op:
            res.append((inst.PRINT, '%sing packages ...' % op.capitalize()))
        elif op.startswith('RM_'):
            res.append((inst.PRINT, 'Pruning %s packages from the cache ...' % op[3:].lower()))
        if op in inst.progress_cmds:
            res.append((inst.PROGRESS, '%d' % len(actions[op])))
        for arg in actions[op]:
            res.append((op, arg))
    return res


# force_linked_actions has now been folded into this function, and is enabled by
# supplying an index and setting force=True
def ensure_linked_actions(dists, prefix, index=None, force=False, always_copy=False):
    actions = defaultdict(list)
    actions[inst.PREFIX] = prefix
    actions['op_order'] = (inst.RM_FETCHED, inst.FETCH, inst.RM_EXTRACTED,
                           inst.EXTRACT, inst.UNLINK, inst.LINK)
    for dist in dists:
        fetched_in = install.is_fetched(dist)
        extracted_in = install.is_extracted(dist)

        if fetched_in and index is not None:
            # Test the MD5, and possibly re-fetch
            fn = dist + '.tar.bz2'
            try:
                if md5_file(fetched_in) != index[fn]['md5']:
                    # RM_FETCHED now removes the extracted data too
                    actions[inst.RM_FETCHED].append(dist)
                    # Re-fetch, re-extract, re-link
                    fetched_in = extracted_in = None
                    force = True
            except KeyError:
                sys.stderr.write('Warning: cannot lookup MD5 of: %s' % fn)

        if not force and install.is_linked(prefix, dist):
            continue

        if extracted_in and force:
            # Always re-extract in the force case
            actions[inst.RM_EXTRACTED].append(dist)
            extracted_in = None

        # Otherwise we need to extract, and possibly fetch
        if not extracted_in and not fetched_in:
            # If there is a cache conflict, clean it up
            fetched_in, conflict = install.find_new_location(dist)
            fetched_in = join(fetched_in, install.dist2filename(dist))
            if conflict is not None:
                actions[inst.RM_FETCHED].append(conflict)
            actions[inst.FETCH].append(dist)

        if not extracted_in:
            actions[inst.EXTRACT].append(dist)

        fetched_dist = extracted_in or fetched_in[:-8]
        fetched_dir = dirname(fetched_dist)

        try:
            # Determine what kind of linking is necessary
            if not extracted_in:
                # If not already extracted, create some dummy
                # data to test with
                install.rm_rf(fetched_dist)
                ppath = join(fetched_dist, 'info')
                os.makedirs(ppath)
                index_json = join(ppath, 'index.json')
                with open(index_json, 'w'):
                    pass
            if config_always_copy or always_copy:
                lt = install.LINK_COPY
            elif install.try_hard_link(fetched_dir, prefix, dist):
                lt = install.LINK_HARD
            elif allow_softlinks and sys.platform != 'win32':
                lt = install.LINK_SOFT
            else:
                lt = install.LINK_COPY
            actions[inst.LINK].append('%s %d' % (dist, lt))
        except (OSError, IOError):
            actions[inst.LINK].append(dist)
        finally:
            if not extracted_in:
                # Remove the dummy data
                try:
                    install.rm_rf(fetched_dist)
                except (OSError, IOError):
                    pass

    return actions

# -------------------------------------------------------------------


def is_root_prefix(prefix):
    return abspath(prefix) == abspath(root_dir)


def add_defaults_to_specs(r, linked, specs, update=False):
    # TODO: This should use the pinning mechanism. But don't change the API:
    # cas uses it.
    if r.explicit(specs):
        return
    log.debug('H0 specs=%r' % specs)
    names_linked = {install.name_dist(dist): dist for dist in linked}
    mspecs = list(map(MatchSpec, specs))

    for name, def_ver in [('python', default_python),
                          # Default version required, but only used for Python
                          ('lua', None)]:
        if any(s.name == name and not s.is_simple() for s in mspecs):
            # if any of the specifications mention the Python/Numpy version,
            # we don't need to add the default spec
            log.debug('H1 %s' % name)
            continue

        depends_on = {s for s in mspecs if r.depends_on(s, name)}
        any_depends_on = bool(depends_on)
        log.debug('H2 %s %s' % (name, any_depends_on))

        if not any_depends_on:
            # if nothing depends on Python/Numpy AND the Python/Numpy is not
            # specified, we don't need to add the default spec
            log.debug('H2A %s' % name)
            continue

        if any(s.is_exact() for s in depends_on):
            # If something depends on Python/Numpy, but the spec is very
            # explicit, we also don't need to add the default spec
            log.debug('H2B %s' % name)
            continue

        if name in names_linked:
            # if Python/Numpy is already linked, we add that instead of the
            # default
            log.debug('H3 %s' % name)
            fkey = names_linked[name] + '.tar.bz2'
            info = r.index[fkey]
            ver = '.'.join(info['version'].split('.', 2)[:2])
            spec = '%s %s* (target=%s)' % (info['name'], ver, fkey)
            specs.append(spec)
            continue

        if name == 'python' and def_ver.startswith('3.'):
            # Don't include Python 3 in the specs if this is the Python 3
            # version of conda.
            continue

        if def_ver is not None:
            specs.append('%s %s*' % (name, def_ver))
    log.debug('HF specs=%r' % specs)


def get_pinned_specs(prefix):
    pinfile = join(prefix, 'conda-meta', 'pinned')
    if not exists(pinfile):
        return []
    with open(pinfile) as f:
        return [i for i in f.read().strip().splitlines() if i and not i.strip().startswith('#')]

def install_actions(prefix, index, specs, force=False, only_names=None, always_copy=False,
                    pinned=True, minimal_hint=False, update_deps=True, prune=False):
    r = Resolve(index)
    linked = r.installed

    if self_update and is_root_prefix(prefix):
        specs.append('conda')

    if pinned:
        pinned_specs = get_pinned_specs(prefix)
        log.debug("Pinned specs=%s" % pinned_specs)
        specs += pinned_specs

    must_have = {}
    if track_features:
        specs.extend(x + '@' for x in track_features)

    pkgs = r.install(specs, linked, update_deps=update_deps)

    for fn in pkgs:
        dist = fn[:-8]
        name = install.name_dist(dist)
        if not name or only_names and name not in only_names:
            continue
        must_have[name] = dist

    if is_root_prefix(prefix):
        for name in foreign:
            if name in must_have:
                del must_have[name]
    elif basename(prefix).startswith('_'):
        # anything (including conda) can be installed into environments
        # starting with '_', mainly to allow conda-build to build conda
        pass
    else:
        # disallow conda from being installed into all other environments
        if 'conda' in must_have or 'conda-env' in must_have:
            sys.exit("Error: 'conda' can only be installed into the "
                     "root environment")

    smh = r.dependency_sort(must_have)

    actions = ensure_linked_actions(
        smh, prefix,
        index=index if force else None,
        force=force, always_copy=always_copy)

    if actions[inst.LINK]:
        actions[inst.SYMLINK_CONDA] = [root_dir]

    for fkey in sorted(linked):
        dist = fkey[:-8]
        name = install.name_dist(dist)
        replace_existing = name in must_have and dist != must_have[name]
        prune_it = prune and dist not in smh
        if replace_existing or prune_it:
            add_unlink(actions, dist)

    return actions


def remove_actions(prefix, specs, index, force=False, pinned=True):
    r = Resolve(index)
    linked = r.installed

    if force:
        mss = list(map(MatchSpec, specs))
        nlinked = {r.package_name(fn): fn[:-8]
                   for fn in linked
                   if not any(r.match(ms, fn) for ms in mss)}
    else:
        add_defaults_to_specs(r, linked, specs, update=True)
        nlinked = {r.package_name(fn): fn[:-8] for fn in r.remove(specs, linked)}

    if pinned:
        pinned_specs = get_pinned_specs(prefix)
        log.debug("Pinned specs=%s" % pinned_specs)

    linked = {r.package_name(fn): fn[:-8] for fn in linked}

    actions = ensure_linked_actions(r.dependency_sort(nlinked), prefix)
    for old_fn in reversed(r.dependency_sort(linked)):
        dist = old_fn + '.tar.bz2'
        name = r.package_name(dist)
        if old_fn == nlinked.get(name, ''):
            continue
        if pinned and any(r.match(ms, dist) for ms in pinned_specs):
            msg = "Cannot remove %s becaue it is pinned. Use --no-pin to override."
            raise RuntimeError(msg % dist)
        if name == 'conda' and name not in nlinked:
            if any(s.split(' ', 1)[0] == 'conda' for s in specs):
                sys.exit("Error: 'conda' cannot be removed from the root environment")
            else:
                msg = ("Error: this 'remove' command cannot be executed because it\n"
                       "would require removing 'conda' dependencies")
                sys.exit(msg)
        add_unlink(actions, old_fn)

    return actions


def remove_features_actions(prefix, index, features):
    r = Resolve(index)
    linked = r.installed

    actions = defaultdict(list)
    actions[inst.PREFIX] = prefix
    _linked = [d + '.tar.bz2' for d in linked]
    to_link = []
    for dist in sorted(linked):
        fn = dist + '.tar.bz2'
        if fn not in index:
            continue
        if r.track_features(fn).intersection(features):
            add_unlink(actions, dist)
        if r.features(fn).intersection(features):
            add_unlink(actions, dist)
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
        add_unlink(actions, dist)

    return actions

# ---------------------------- EXECUTION --------------------------


def execute_actions(actions, index=None, verbose=False):
    plan = plan_from_actions(actions)
    with History(actions[inst.PREFIX]):
        inst.execute_instructions(plan, index, verbose)


def update_old_plan(old_plan):
    """
    Update an old plan object to work with
    `conda.instructions.execute_instructions`
    """
    plan = []
    for line in old_plan:
        if line.startswith('#'):
            continue
        if ' ' not in line:
            raise CondaException(
                "The instruction '%s' takes at least one argument" % line
            )

        instruction, arg = line.split(' ', 1)
        plan.append((instruction, arg))
    return plan


def execute_plan(old_plan, index=None, verbose=False):
    """
    Deprecated: This should `conda.instructions.execute_instructions` instead
    """
    plan = update_old_plan(old_plan)
    inst.execute_instructions(plan, index, verbose)


if __name__ == '__main__':
    # for testing new revert_actions() only
    from pprint import pprint
    pprint(dict(revert_actions(sys.prefix, int(sys.argv[1]))))
