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
from os.path import abspath, basename, isfile, join, exists

from conda import config
from conda import install
from conda.history import History
from conda.resolve import MatchSpec, Resolve, Package
from conda.utils import md5_file, human_bytes
from conda import instructions as inst
from conda.exceptions import CondaException
from conda.compat import iteritems, itervalues

# For backwards compatibility
from conda.instructions import (FETCH, EXTRACT, UNLINK, LINK, RM_EXTRACTED,  # noqa
                                RM_FETCHED, PREFIX, PRINT, PROGRESS,
                                SYMLINK_CONDA)

log = getLogger(__name__)

def print_dists(dists_extras):
    fmt = "    %-27s|%17s"
    print(fmt % ('package', 'build'))
    print(fmt % ('-' * 27, '-' * 17))
    for dist, extra in dists_extras:
        line = fmt % tuple(dist.rsplit('-', 1))
        if extra:
            line += extra
        print(line)


def display_actions(actions, index, show_channel_urls=None):
    if show_channel_urls is None:
        show_channel_urls = config.show_channel_urls
    if actions.get(inst.FETCH):
        print("\nThe following packages will be downloaded:\n")

        disp_lst = []
        for dist in actions[inst.FETCH]:
            info = index[dist + '.tar.bz2']
            extra = '%15s' % human_bytes(info['size'])
            if show_channel_urls:
                extra += '  %s' % config.canonical_channel_name(
                                       info.get('channel'))
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

    # This assumes each package will appear in LINK no more than once.
    Packages = {}
    linktypes = {}
    for arg in actions.get(inst.LINK, []):
        dist, pkgs_dir, lt = inst.split_linkarg(arg)
        pkg, ver, build = dist.rsplit('-', 2)
        packages[pkg][1] = ver + '-' + build
        Packages[dist] = Package(dist + '.tar.bz2', index[dist + '.tar.bz2'])
        linktypes[pkg] = lt
        features[pkg][1] = index[dist + '.tar.bz2'].get('features', '')
    for arg in actions.get(inst.UNLINK, []):
        dist, pkgs_dir, lt = inst.split_linkarg(arg)
        pkg, ver, build = dist.rsplit('-', 2)
        packages[pkg][0] = ver + '-' + build
        # If the package is not in the index (e.g., an installed
        # package that is not in the index any more), we just have to fake the metadata.
        default = dict(name=pkg, version=ver, build=build, channel=None,
                       build_number=int(build) if build.isdigit() else 0)
        info = index.get(dist + ".tar.bz2", default)
        Packages[dist] = Package(dist + '.tar.bz2', info)
        features[pkg][0] = info.get('features', '')

    #                     Put a minimum length here---.    .--For the :
    #                                                 v    v
    maxpkg = max(len(max(packages or [''], key=len)), 0) + 1
    maxoldver = len(max(packages.values() or [['']], key=lambda i: len(i[0]))[0])
    maxnewver = len(max(packages.values() or [['', '']], key=lambda i: len(i[1]))[1])
    maxoldfeatures = len(max(features.values() or [['']], key=lambda i: len(i[0]))[0])
    maxnewfeatures = len(max(features.values() or [['', '']], key=lambda i: len(i[1]))[1])

    name = config.canonical_channel_name
    maxoldchannel = len(max([name(Packages[p + '-' + packages[p][0]].channel)
                             for p in packages if packages[p][0]] or [''], key=len))
    maxnewchannel = len(max([name(Packages[p + '-' + packages[p][1]].channel)
                             for p in packages if packages[p][1]] or [''], key=len))
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
        if show_channel_urls:
            oldfmt[pkg] += ' {channel[0]:<%s}' % maxoldchannel
        if packages[pkg][0]:
            newfmt[pkg] = '{vers[1]:<%s}' % maxnewver
        else:
            newfmt[pkg] = '{pkg:<%s} {vers[1]:<%s}' % (maxpkg, maxnewver)
        if show_channel_urls:
            newfmt[pkg] += ' {channel[1]:<%s}' % maxnewchannel
        # TODO: Should we also care about the old package's link type?
        if pkg in linktypes and linktypes[pkg] != install.LINK_HARD:
            newfmt[pkg] += ' (%s)' % install.link_name_map[linktypes[pkg]]

        if features[pkg][0]:
            oldfmt[pkg] += ' [{features[0]:<%s}]' % maxoldfeatures
        if features[pkg][1]:
            newfmt[pkg] += ' [{features[1]:<%s}]' % maxnewfeatures

        if pkg in new or pkg in removed:
            continue
        P0 = Packages[pkg + '-' + packages[pkg][0]]
        P1 = Packages[pkg + '-' + packages[pkg][1]]
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
        channel = ['', '']
        for i in range(2):
            if packages[pkg][i]:
                p = Packages[pkg + '-' + packages[pkg][i]].channel
                channel[i] = config.canonical_channel_name(p)
        return lead + s.format(pkg=pkg + ':', vers=packages[pkg],
                               channel=channel, features=features[pkg])

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
        if op in inst.progress_cmds:
            res.append((inst.PROGRESS, '%d' % len(actions[op])))
        for arg in actions[op]:
            res.append((op, arg))
    return res


def extracted_where(dist):
    for pkgs_dir in config.pkgs_dirs:
        if install.is_extracted(pkgs_dir, dist):
            return pkgs_dir
    return None


def ensure_linked_actions(dists, prefix):
    actions = defaultdict(list)
    actions[inst.PREFIX] = prefix
    for dist in dists:
        if install.is_linked(prefix, dist):
            continue

        extracted_in = extracted_where(dist)
        if extracted_in:
            if config.always_copy:
                lt = install.LINK_COPY
            elif install.try_hard_link(extracted_in, prefix, dist):
                lt = install.LINK_HARD
            elif config.allow_softlinks and sys.platform != 'win32':
                lt = install.LINK_SOFT
            else:
                lt = install.LINK_COPY
            actions[inst.LINK].append('%s %s %d' % (dist, extracted_in, lt))
        else:
            # Make a guess from the first pkgs dir, which is where it will be
            # extracted
            try:
                os.makedirs(join(config.pkgs_dirs[0], dist, 'info'))
                index_json = join(config.pkgs_dirs[0], dist, 'info',
                                  'index.json')
                with open(index_json, 'w'):
                    pass
                if config.always_copy:
                    lt = install.LINK_COPY
                elif install.try_hard_link(config.pkgs_dirs[0], prefix, dist):
                    lt = install.LINK_HARD
                elif config.allow_softlinks and sys.platform != 'win32':
                    lt = install.LINK_SOFT
                else:
                    lt = install.LINK_COPY
                actions[inst.LINK].append('%s %s %d' % (dist, config.pkgs_dirs[0], lt))
            except (OSError, IOError):
                actions[inst.LINK].append(dist)
            finally:
                try:
                    install.rm_rf(join(config.pkgs_dirs[0], dist))
                except (OSError, IOError):
                    pass

            actions[inst.EXTRACT].append(dist)
            if install.is_fetched(config.pkgs_dirs[0], dist):
                continue
            actions[inst.FETCH].append(dist)
    return actions


def force_linked_actions(dists, index, prefix):
    actions = defaultdict(list)
    actions[inst.PREFIX] = prefix
    actions['op_order'] = (inst.RM_FETCHED, inst.FETCH, inst.RM_EXTRACTED,
                           inst.EXTRACT, inst.UNLINK, inst.LINK)
    for dist in dists:
        fn = dist + '.tar.bz2'
        pkg_path = join(config.pkgs_dirs[0], fn)
        if isfile(pkg_path):
            try:
                if md5_file(pkg_path) != index[fn]['md5']:
                    actions[inst.RM_FETCHED].append(dist)
                    actions[inst.FETCH].append(dist)
            except KeyError:
                sys.stderr.write('Warning: cannot lookup MD5 of: %s' % fn)
        else:
            actions[inst.FETCH].append(dist)
        actions[inst.RM_EXTRACTED].append(dist)
        actions[inst.EXTRACT].append(dist)
        if isfile(join(prefix, 'conda-meta', dist + '.json')):
            add_unlink(actions, dist)
        actions[inst.LINK].append(dist)
    return actions

# -------------------------------------------------------------------


def is_root_prefix(prefix):
    return abspath(prefix) == abspath(config.root_dir)


def dist2spec3v(dist):
    name, version, unused_build = dist.rsplit('-', 2)
    return '%s %s*' % (name, version[:3])


def add_defaults_to_specs(r, linked, specs, update=False):
    # TODO: This should use the pinning mechanism. But don't change the API:
    # cas uses it.
    if r.explicit(specs):
        return
    log.debug('H0 specs=%r' % specs)
    names_linked = {install.name_dist(dist): dist for dist in linked}
    names_ms = {MatchSpec(s).name: MatchSpec(s) for s in specs}

    for name, def_ver in [('python', config.default_python),
                          # Default version required, but only used for Python
                          ('lua', None)]:
        ms = names_ms.get(name)
        if ms and ms.strictness > 1:
            # if any of the specifications mention the Python/Numpy version,
            # we don't need to add the default spec
            log.debug('H1 %s' % name)
            continue

        any_depends_on = any(ms2.name == name
                             for spec in specs
                             for fn in r.find_matches(spec)
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
            spec = dist2spec3v(names_linked[name])
            if update:
                spec = '%s (target=%s.tar.bz2)' % (spec, names_linked[name])
            specs.append(spec)
            continue

        if (name, def_ver) in [('python', '3.3'), ('python', '3.4'),
                               ('python', '3.5')]:
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
        return [i for i in f.read().strip().splitlines() if i and not i.strip().startswith('#')]

def install_actions(prefix, index, specs, force=False, only_names=None,
                    pinned=True, minimal_hint=False, update_deps=True, prune=False):
    r = Resolve(index)
    linked = install.linked(prefix)

    if config.self_update and is_root_prefix(prefix):
        specs.append('conda')

    if pinned:
        pinned_specs = get_pinned_specs(prefix)
        log.debug("Pinned specs=%s" % pinned_specs)
        specs += pinned_specs

    must_have = {}
    if config.track_features:
        specs.extend(x + '@' for x in config.track_features)

    pkgs = r.install(specs, [d + '.tar.bz2' for d in linked], update_deps=update_deps)
    for fn in pkgs:
        dist = fn[:-8]
        name = install.name_dist(dist)
        if not name or only_names and name not in only_names:
            continue
        must_have[name] = dist

    if is_root_prefix(prefix):
        for name in config.foreign:
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

    if force:
        actions = force_linked_actions(smh, index, prefix)
    else:
        actions = ensure_linked_actions(smh, prefix)

    if actions[inst.LINK]:
        actions[inst.SYMLINK_CONDA] = [config.root_dir]

    for dist in sorted(linked):
        name = install.name_dist(dist)
        replace_existing = name in must_have and dist != must_have[name]
        prune_it = prune and dist not in smh
        if replace_existing or prune_it:
            add_unlink(actions, dist)

    return actions


def remove_actions(prefix, specs, index=None, force=False, pinned=True):
    linked = install.linked_data(prefix)

    if not force:
        installed = {fn + '.tar.bz2': rec for fn, rec in iteritems(linked)}
        r = Resolve(installed)
        installed = installed.keys()
        force = r.bad_installed(installed, [])[0] is not None
    if force:
        nspecs = set(rec['name'] for rec in itervalues(linked) if rec['name'] not in specs)
    else:
        if config.track_features:
            specs = list(specs) + [x + '@' for x in config.track_features]
        nspecs = set(linked[fn[:-8]]['name'] for fn in r.remove(specs, installed))

    if pinned:
        pinned_specs = get_pinned_specs(prefix)
        log.debug("Pinned specs=%s" % pinned_specs)

    actions = defaultdict(list)
    actions[inst.PREFIX] = prefix
    lmap = {rec['name']: fn for fn, rec in iteritems(linked)}
    for dist in reversed(r.dependency_sort(lmap)):
        name = linked[dist]['name']
        if name in nspecs:
            continue
        if pinned and name in pinned_specs:
            msg = "Cannot remove %s becaue it is pinned. Use --no-pin to override."
            raise RuntimeError(msg % dist)
        if name == 'conda':
            if name in specs:
                sys.exit("Error: 'conda' cannot be removed from the root environment")
            else:
                msg = ("Error: this 'remove' command cannot be executed because it\n"
                       "would require removing 'conda' dependencies")
                sys.exit(msg)
        add_unlink(actions, dist)

    return actions


def remove_features_actions(prefix, index, features):
    linked = install.linked(prefix)
    r = Resolve(index)

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
