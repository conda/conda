"""
Handle the planning of installs and their execution.

NOTE:
    conda.install uses canonical package names in its interface functions,
    whereas conda.resolve uses package filenames, as those are used as index
    keys.  We try to keep fixes to this "impedance mismatch" local to this
    module.
"""
from __future__ import absolute_import, division, print_function, unicode_literals

from collections import defaultdict, namedtuple
from logging import getLogger
from os.path import abspath, basename, exists, join
import sys

from . import instructions as inst
from ._vendor.boltons.setutils import IndexedSet
from .base.constants import DEFAULTS_CHANNEL_NAME, UNKNOWN_CHANNEL
from .base.context import context
from .cli import common
from .cli.common import pkg_if_in_private_env, prefix_if_in_private_env
from .common.compat import odict, on_win
from .common.path import (is_private_env, preferred_env_matches_prefix,
                          preferred_env_to_prefix, prefix_to_env_name)
from .core.index import _supplement_index_with_prefix
from .core.linked_data import is_linked, linked_data
from .core.package_cache import ProgressiveFetchExtract
from .exceptions import (ArgumentError, CondaIndexError, CondaRuntimeError,
                         InstallError, RemoveError)
from .history import History
from .instructions import (ACTION_CODES, CHECK_EXTRACT, CHECK_FETCH, EXTRACT, FETCH, LINK, PREFIX,
                           PRINT, PROGRESS, PROGRESSIVEFETCHEXTRACT, PROGRESS_COMMANDS,
                           RM_EXTRACTED, RM_FETCHED, SYMLINK_CONDA, UNLINK,
                           UNLINKLINKTRANSACTION, execute_instructions)
from .models.channel import Channel
from .models.dist import Dist
from .models.enums import LinkType
from .resolve import MatchSpec, Resolve
from .utils import human_bytes
from .version import normalized_version

try:
    from cytoolz.itertoolz import concatv, groupby
except ImportError:
    from ._vendor.toolz.itertoolz import concatv, groupby  # NOQA

log = getLogger(__name__)


def print_dists(dists_extras):
    fmt = "    %-27s|%17s"
    print(fmt % ('package', 'build'))
    print(fmt % ('-' * 27, '-' * 17))
    for dist, extra in dists_extras:
        name, version, build, _ = dist.quad
        line = fmt % (name + '-' + version, build)
        if extra:
            line += extra
        print(line)


def display_actions(actions, index, show_channel_urls=None):
    if show_channel_urls is None:
        show_channel_urls = context.show_channel_urls

    def channel_str(rec):
        if rec.get('schannel'):
            return rec['schannel']
        if rec.get('url'):
            return Channel(rec['url']).canonical_name
        if rec.get('channel'):
            return Channel(rec['channel']).canonical_name
        return UNKNOWN_CHANNEL

    def channel_filt(s):
        if show_channel_urls is False:
            return ''
        if show_channel_urls is None and s == DEFAULTS_CHANNEL_NAME:
            return ''
        return s

    if actions.get(FETCH):
        print("\nThe following packages will be downloaded:\n")

        disp_lst = []
        for dist in actions[FETCH]:
            dist = Dist(dist)
            info = index[dist]
            extra = '%15s' % human_bytes(info['size'])
            schannel = channel_filt(channel_str(info))
            if schannel:
                extra += '  ' + schannel
            disp_lst.append((dist, extra))
        print_dists(disp_lst)

        if index and len(actions[FETCH]) > 1:
            num_bytes = sum(index[Dist(dist)]['size'] for dist in actions[FETCH])
            print(' ' * 4 + '-' * 60)
            print(" " * 43 + "Total: %14s" % human_bytes(num_bytes))

    # package -> [oldver-oldbuild, newver-newbuild]
    packages = defaultdict(lambda: list(('', '')))
    features = defaultdict(lambda: list(('', '')))
    channels = defaultdict(lambda: list(('', '')))
    records = defaultdict(lambda: list((None, None)))
    linktypes = {}

    for arg in actions.get(LINK, []):
        dist = Dist(arg)
        rec = index[dist]
        pkg = rec['name']
        channels[pkg][1] = channel_str(rec)
        packages[pkg][1] = rec['version'] + '-' + rec['build']
        records[pkg][1] = rec
        linktypes[pkg] = LinkType.hardlink  # TODO: this is a lie; may have to give this report after UnlinkLinkTransaction.verify()  # NOQA
        features[pkg][1] = rec.get('features', '')
    for arg in actions.get(UNLINK, []):
        dist = Dist(arg)
        rec = index[dist]
        pkg = rec['name']
        channels[pkg][0] = channel_str(rec)
        packages[pkg][0] = rec['version'] + '-' + rec['build']
        records[pkg][0] = rec
        features[pkg][0] = rec.get('features', '')

    new = {p for p in packages if not packages[p][0]}
    removed = {p for p in packages if not packages[p][1]}
    # New packages are actually listed in the left-hand column,
    # so let's move them over there
    for pkg in new:
        for var in (packages, features, channels, records):
            var[pkg] = var[pkg][::-1]

    empty = False
    if packages:
        maxpkg = max(len(p) for p in packages) + 1
        maxoldver = max(len(p[0]) for p in packages.values())
        maxnewver = max(len(p[1]) for p in packages.values())
        maxoldfeatures = max(len(p[0]) for p in features.values())
        maxnewfeatures = max(len(p[1]) for p in features.values())
        maxoldchannels = max(len(channel_filt(p[0])) for p in channels.values())
        maxnewchannels = max(len(channel_filt(p[1])) for p in channels.values())
    else:
        empty = True

    updated = set()
    downgraded = set()
    channeled = set()
    oldfmt = {}
    newfmt = {}
    for pkg in packages:
        # That's right. I'm using old-style string formatting to generate a
        # string with new-style string formatting.
        oldfmt[pkg] = '{pkg:<%s} {vers[0]:<%s}' % (maxpkg, maxoldver)
        if maxoldchannels:
            oldfmt[pkg] += ' {channels[0]:<%s}' % maxoldchannels
        if features[pkg][0]:
            oldfmt[pkg] += ' [{features[0]:<%s}]' % maxoldfeatures

        lt = LinkType(linktypes.get(pkg, LinkType.hardlink))
        lt = '' if lt == LinkType.hardlink else (' (%s)' % lt)
        if pkg in removed or pkg in new:
            oldfmt[pkg] += lt
            continue

        newfmt[pkg] = '{vers[1]:<%s}' % maxnewver
        if maxnewchannels:
            newfmt[pkg] += ' {channels[1]:<%s}' % maxnewchannels
        if features[pkg][1]:
            newfmt[pkg] += ' [{features[1]:<%s}]' % maxnewfeatures
        newfmt[pkg] += lt

        P0 = records[pkg][0]
        P1 = records[pkg][1]
        pri0 = P0.get('priority')
        pri1 = P1.get('priority')
        if pri0 is None or pri1 is None:
            pri0 = pri1 = 1
        try:
            if str(P1.version) == 'custom':
                newver = str(P0.version) != 'custom'
                oldver = not newver
            else:
                # <= here means that unchanged packages will be put in updated
                N0 = normalized_version(P0.version)
                N1 = normalized_version(P1.version)
                newver = N0 < N1
                oldver = N0 > N1
        except TypeError:
            newver = P0.version < P1.version
            oldver = P0.version > P1.version
        oldbld = P0.build_number > P1.build_number
        newbld = P0.build_number < P1.build_number
        if context.channel_priority and pri1 < pri0 and (oldver or not newver and not newbld):
            channeled.add(pkg)
        elif newver:
            updated.add(pkg)
        elif pri1 < pri0 and (oldver or not newver and oldbld):
            channeled.add(pkg)
        elif oldver:
            downgraded.add(pkg)
        elif not oldbld:
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
            # New packages have been moved to the "old" column for display
            print(format(oldfmt[pkg], pkg))

    if removed:
        print("\nThe following packages will be REMOVED:\n")
        for pkg in sorted(removed):
            print(format(oldfmt[pkg], pkg))

    if updated:
        print("\nThe following packages will be UPDATED:\n")
        for pkg in sorted(updated):
            print(format(oldfmt[pkg] + arrow + newfmt[pkg], pkg))

    if channeled:
        print("\nThe following packages will be SUPERSEDED by a higher-priority channel:\n")
        for pkg in sorted(channeled):
            print(format(oldfmt[pkg] + arrow + newfmt[pkg], pkg))

    if downgraded:
        print("\nThe following packages will be DOWNGRADED due to dependency conflicts:\n")
        for pkg in sorted(downgraded):
            print(format(oldfmt[pkg] + arrow + newfmt[pkg], pkg))

    if empty and actions.get(SYMLINK_CONDA):
        print("\nThe following empty environments will be CREATED:\n")
        print(actions['PREFIX'])

    print()


def nothing_to_do(actions):
    for op in ACTION_CODES:
        if actions.get(op):
            return False
    return True


def add_unlink(actions, dist):
    assert isinstance(dist, Dist)
    if UNLINK not in actions:
        actions[UNLINK] = []
    actions[UNLINK].append(dist)


def handle_menuinst(unlink_dists, link_dists):
    if not on_win:
        return unlink_dists, link_dists

    # Always link/unlink menuinst first/last on windows in case a subsequent
    # package tries to import it to create/remove a shortcut

    # unlink
    menuinst_idx = next((q for q, d in enumerate(unlink_dists) if d.name == 'menuinst'), None)
    if menuinst_idx is not None:
        unlink_dists = tuple(concatv(
            unlink_dists[:menuinst_idx],
            unlink_dists[menuinst_idx+1:],
            unlink_dists[menuinst_idx:menuinst_idx+1],
        ))

    # link
    menuinst_idx = next((q for q, d in enumerate(link_dists) if d.name == 'menuinst'), None)
    if menuinst_idx is not None:
        link_dists = tuple(concatv(
            link_dists[menuinst_idx:menuinst_idx+1],
            link_dists[:menuinst_idx],
            link_dists[menuinst_idx+1:],
        ))

    return unlink_dists, link_dists


def inject_UNLINKLINKTRANSACTION(plan, index, prefix):
    # TODO: we really shouldn't be mutating the plan list here; turn plan into a tuple
    first_unlink_link_idx = next((q for q, p in enumerate(plan) if p[0] in (UNLINK, LINK)), -1)
    if first_unlink_link_idx >= 0:
        grouped_instructions = groupby(lambda x: x[0], plan)
        unlink_dists = tuple(Dist(d[1]) for d in grouped_instructions.get(UNLINK, ()))
        link_dists = tuple(Dist(d[1]) for d in grouped_instructions.get(LINK, ()))
        unlink_dists, link_dists = handle_menuinst(unlink_dists, link_dists)

        # TODO: ideally we'd move these two lines before both the y/n confirmation and the --dry-run exit  # NOQA
        pfe = ProgressiveFetchExtract(index, link_dists)
        pfe.prepare()

        plan.insert(first_unlink_link_idx, (UNLINKLINKTRANSACTION, (unlink_dists, link_dists)))
        plan.insert(first_unlink_link_idx, (PROGRESSIVEFETCHEXTRACT, pfe))

    return plan


def plan_from_actions(actions, index):
    if 'op_order' in actions and actions['op_order']:
        op_order = actions['op_order']
    else:
        op_order = ACTION_CODES

    assert PREFIX in actions and actions[PREFIX]
    prefix = actions[PREFIX]
    plan = [('PREFIX', '%s' % actions[PREFIX])]

    log.debug("Adding plans for operations: {0}".format(op_order))
    for op in op_order:
        if op not in actions:
            log.trace("action {0} not in actions".format(op))
            continue
        if not actions[op]:
            log.trace("action {0} has None value".format(op))
            continue
        if '_' not in op:
            plan.append((PRINT, '%sing packages ...' % op.capitalize()))
        elif op.startswith('RM_'):
            plan.append((PRINT, 'Pruning %s packages from the cache ...' % op[3:].lower()))
        if op in PROGRESS_COMMANDS:
            plan.append((PROGRESS, '%d' % len(actions[op])))
        for arg in actions[op]:
            log.debug("appending value {0} for action {1}".format(arg, op))
            plan.append((op, arg))

    plan = inject_UNLINKLINKTRANSACTION(plan, index, prefix)

    return plan


# force_linked_actions has now been folded into this function, and is enabled by
# supplying an index and setting force=True
def ensure_linked_actions(dists, prefix, index=None, force=False,
                          always_copy=False):
    assert all(isinstance(d, Dist) for d in dists)
    actions = defaultdict(list)
    actions[PREFIX] = prefix
    actions['op_order'] = (CHECK_FETCH, RM_FETCHED, FETCH, CHECK_EXTRACT,
                           RM_EXTRACTED, EXTRACT,
                           UNLINK, LINK, SYMLINK_CONDA)

    for dist in dists:
        if not force and is_linked(prefix, dist):
            continue
        actions[LINK].append(dist)
    return actions

# -------------------------------------------------------------------


def is_root_prefix(prefix):
    return abspath(prefix) == abspath(context.root_prefix)


def add_defaults_to_specs(r, linked, specs, update=False, prefix=None):
    # TODO: This should use the pinning mechanism. But don't change the API because cas uses it
    if r.explicit(specs) or is_private_env(prefix):
        return
    log.debug('H0 specs=%r' % specs)
    names_linked = {r.package_name(d): d for d in linked if d in r.index}
    mspecs = list(map(MatchSpec, specs))

    for name, def_ver in [('python', context.default_python or None),
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
            # if Python/Numpy is already linked, we add that instead of the default
            log.debug('H3 %s' % name)
            dist = Dist(names_linked[name])
            info = r.index[dist]
            ver = '.'.join(info['version'].split('.', 2)[:2])
            spec = '%s %s* (target=%s)' % (info['name'], ver, dist)
            specs.append(spec)
            continue

        if name == 'python' and def_ver and def_ver.startswith('3.'):
            # Don't include Python 3 in the specs if this is the Python 3
            # version of conda.
            continue

        if def_ver is not None:
            specs.append('%s %s*' % (name, def_ver))
    log.debug('HF specs=%r' % specs)


def get_pinned_specs(prefix):
    pinfile = join(prefix, 'conda-meta', 'pinned')
    if exists(pinfile):
        with open(pinfile) as f:
            from_file = (i for i in f.read().strip().splitlines()
                         if i and not i.strip().startswith('#'))
    else:
        from_file = ()

    from .cli.common import spec_from_line

    def munge_spec(s):
        return s if ' ' in s else spec_from_line(s)

    return tuple(munge_spec(s) for s in concatv(context.pinned_packages, from_file))


# Has one spec (string) for each env
SpecForEnv = namedtuple('DistForEnv', ['env', 'spec'])
# Has several spec (strings) for each prefix and the related r value
SpecsForPrefix = namedtuple('DistsForPrefix', ['prefix', 'specs', 'r'])


def install_actions(prefix, index, specs, force=False, only_names=None, always_copy=False,
                    pinned=True, minimal_hint=False, update_deps=True, prune=False,
                    channel_priority_map=None, is_update=False):  # pragma: no cover
    """
    This function ignores preferred_env.  It's currently used extensively by conda-build, but
    it is no longer used within the conda code.  Instead, we now use `install_actions_list()`.
    """
    # type: (str, Dict[Dist, Record], List[str], bool, Option[List[str]], bool, bool, bool,
    #        bool, bool, bool, Dict[str, Sequence[str, int]]) -> Dict[weird]
    r = get_resolve_object(index.copy(), prefix)
    str_specs = specs

    specs_for_prefix = SpecsForPrefix(
        prefix=prefix, specs=tuple(str_specs), r=r
    )
    actions = get_actions_for_dists(specs_for_prefix, only_names, index, force, always_copy, prune,
                                    update_deps, pinned)
    return actions


def install_actions_list(prefix, index, specs, force=False, only_names=None, always_copy=False,
                         pinned=True, minimal_hint=False, update_deps=True, prune=False,
                         channel_priority_map=None, is_update=False):
    # type: (str, Dict[Dist, Record], List[str], bool, Option[List[str]], bool, bool, bool,
    #        bool, bool, bool, Dict[str, Sequence[str, int]]) -> List[Dict[weird]]
    str_specs = specs
    specs = [MatchSpec(spec) for spec in specs]
    r = get_resolve_object(index.copy(), prefix)

    linked_in_root = linked_data(context.root_prefix)

    dists_for_envs = determine_all_envs(r, specs, channel_priority_map=channel_priority_map)
    ensure_packge_not_duplicated_in_private_env_root(dists_for_envs, linked_in_root)
    preferred_envs = set(d.env for d in dists_for_envs)

    # Group specs by prefix
    grouped_specs = determine_dists_per_prefix(r, prefix, index, preferred_envs,
                                               dists_for_envs, context)

    # Replace SpecsForPrefix specs with specs that were passed in in order to retain
    #   version information
    required_solves = match_to_original_specs(str_specs, grouped_specs)

    actions = [get_actions_for_dists(dists_by_prefix, only_names, index, force,
                                     always_copy, prune, update_deps, pinned)
               for dists_by_prefix in required_solves]

    # Need to add unlink actions if updating a private env from root
    if is_update and prefix == context.root_prefix:
        add_unlink_options_for_update(actions, required_solves, index)

    return actions


def add_unlink_options_for_update(actions, required_solves, index):
    # type: (Dict[weird], List[SpecsForPrefix], List[weird]) -> ()
    get_action_for_prefix = lambda prfx: tuple(actn for actn in actions if actn["PREFIX"] == prfx)
    linked_in_prefix = linked_data(context.root_prefix)
    spec_in_root = lambda spc: tuple(
        mtch for mtch in linked_in_prefix.keys() if MatchSpec(spc).match(mtch))
    for solved in required_solves:
        # If the solved prefix is private
        if is_private_env(prefix_to_env_name(solved.prefix, context.root_prefix)):
            for spec in solved.specs:
                matched_in_root = spec_in_root(spec)
                if matched_in_root:
                    aug_action = get_action_for_prefix(context.root_prefix)
                    if len(aug_action) > 0:
                        add_unlink(aug_action[0], matched_in_root[0])
                    else:
                        actions.append(remove_actions(context.root_prefix, matched_in_root, index))
        # If the solved prefix is root
        elif preferred_env_matches_prefix(None, solved.prefix, context.root_prefix):
            for spec in solved.specs:
                spec_in_private_env = prefix_if_in_private_env(spec)
                if spec_in_private_env:
                    # remove pkg from private env and install in root
                    aug_action = get_action_for_prefix(spec_in_private_env)
                    if len(aug_action) > 0:
                        add_unlink(aug_action[0], Dist(pkg_if_in_private_env(spec)))
                    else:
                        actions.append(remove_spec_action_from_prefix(
                            spec_in_private_env, Dist(pkg_if_in_private_env(spec))))


def get_resolve_object(index, prefix):
    # instantiate resolve object
    _supplement_index_with_prefix(index, prefix, {})
    r = Resolve(index)
    return r


def determine_all_envs(r, specs, channel_priority_map=None):
    # type: (Record, List[MatchSpec], Option[List[Tuple]] -> List[SpecForEnv]
    assert all(isinstance(spec, MatchSpec) for spec in specs)
    best_pkgs = (r.index[r.get_dists_for_spec(s, emptyok=False)[-1]] for s in specs)
    spec_for_envs = tuple(SpecForEnv(env=p.preferred_env, spec=p.name) for p in best_pkgs)
    return spec_for_envs


def ensure_packge_not_duplicated_in_private_env_root(dists_for_envs, linked_in_root):
    # type: List[DistForEnv], List[(Dist, Record)] -> ()
    for dist_env in dists_for_envs:
        # If trying to install a package in root that is already in a private env
        if dist_env.env is None and common.prefix_if_in_private_env(dist_env.spec) is not None:
            raise InstallError("Package %s is already installed in a private env %s" %
                               (dist_env.spec, dist_env.env))
        # If trying to install a package in a private env that is already in root
        if (is_private_env(dist_env.env) and
                any(dist for dist in linked_in_root if dist.dist_name.startswith(dist_env.spec))):
            raise InstallError("Package %s is already installed in root. Can't install in private"
                               " environment %s" % (dist_env.spec, dist_env.env))


def not_requires_private_env(prefix, preferred_envs):
    if (context.prefix_specified is True or not context.prefix == context.root_prefix or
            all(preferred_env_matches_prefix(preferred_env, prefix, context.root_prefix) for
                preferred_env in preferred_envs)):
        return True
    return False


def determine_dists_per_prefix(r, prefix, index, preferred_envs, dists_for_envs, context):
    # type: (Resolve, string, List[(Dist, Record)], Set[String], List[SpecForEnv]) ->
    #   (List[pecsForPrefix])

    # if len(preferred_envs) == 1 and preferred_env matches prefix
    #    solution is good
    # if len(preferred_envs) == 1 and preferred_env is None
    #    solution is good
    # if len(preferred_envs) == 2 and set([None, preferred_env]) preferred_env matches prefix
    #    solution is good
    if not_requires_private_env(prefix, preferred_envs):
        dists = set(d.spec for d in dists_for_envs)
        prefix_with_dists_no_deps_has_resolve = [SpecsForPrefix(prefix=prefix, r=r, specs=dists)]
    else:
        # Ensure that conda is working in the root dir
        assert context.prefix == context.root_prefix

        def get_r(preferred_env):
            # don't make r for the prefix where we already have it created
            if preferred_env_matches_prefix(preferred_env, prefix, context.root_prefix):
                return r
            else:
                return get_resolve_object(index.copy(), preferred_env_to_prefix(
                    preferred_env, context.root_prefix, context.envs_dirs))

        prefix_with_dists_no_deps_has_resolve = []
        for env in preferred_envs:
            dists = IndexedSet(d.spec for d in dists_for_envs if d.env == env)
            prefix_with_dists_no_deps_has_resolve.append(
                SpecsForPrefix(
                    prefix=preferred_env_to_prefix(env, context.root_prefix, context.envs_dirs),
                    r=get_r(env),
                    specs=dists)
            )
    return prefix_with_dists_no_deps_has_resolve


def match_to_original_specs(str_specs, specs_for_prefix):
    matches_any_spec = lambda dst: next(spc for spc in str_specs if spc.startswith(dst))
    matched_specs_for_prefix = []
    for prefix_with_dists in specs_for_prefix:
        linked = linked_data(prefix_with_dists.prefix)
        r = prefix_with_dists.r
        new_matches = []
        for spec in prefix_with_dists.specs:
            matched = matches_any_spec(spec)
            if matched:
                new_matches.append(matched)
        add_defaults_to_specs(r, linked, new_matches, prefix=prefix_with_dists.prefix)
        matched_specs_for_prefix.append(SpecsForPrefix(
            prefix=prefix_with_dists.prefix, r=prefix_with_dists.r, specs=new_matches))
    return matched_specs_for_prefix


def get_actions_for_dists(dists_for_prefix, only_names, index, force, always_copy, prune,
                          update_deps, pinned):
    root_only = ('conda', 'conda-env')
    prefix = dists_for_prefix.prefix
    dists = dists_for_prefix.specs
    r = dists_for_prefix.r
    specs = [MatchSpec(dist) for dist in dists]
    specs = augment_specs(prefix, specs, pinned)

    linked = linked_data(prefix)
    must_have = odict()

    installed = linked
    if prune:
        installed = []
    pkgs = r.install(specs, installed, update_deps=update_deps)

    for fn in pkgs:
        dist = Dist(fn)
        name = r.package_name(dist)
        if not name or only_names and name not in only_names:
            continue
        must_have[name] = dist

    if is_root_prefix(prefix):
        # for name in foreign:
        #     if name in must_have:
        #         del must_have[name]
        pass
    elif basename(prefix).startswith('_'):
        # anything (including conda) can be installed into environments
        # starting with '_', mainly to allow conda-build to build conda
        pass

    elif any(s in must_have for s in root_only):
        # the solver scheduled an install of conda, but it wasn't in the
        # specs, so it must have been a dependency.
        specs = [s for s in specs if r.depends_on(s, root_only)]
        if specs:
            raise InstallError("""\
Error: the following specs depend on 'conda' and can only be installed
into the root environment: %s""" % (' '.join(spec.name for spec in specs),))
        linked = [r.package_name(s) for s in linked]
        linked = [s for s in linked if r.depends_on(s, root_only)]
        if linked:
            raise InstallError("""\
Error: one or more of the packages already installed depend on 'conda'
and should only be installed in the root environment: %s
These packages need to be removed before conda can proceed.""" % (' '.join(linked),))
        raise InstallError("Error: 'conda' can only be installed into the "
                           "root environment")

    smh = r.dependency_sort(must_have)
    actions = ensure_linked_actions(
        smh, prefix,
        index=r.index,
        force=force, always_copy=always_copy)

    if actions[LINK]:
        actions[SYMLINK_CONDA] = [context.root_prefix]

    for dist in sorted(linked):
        dist = Dist(dist)
        name = r.package_name(dist)
        replace_existing = name in must_have and dist != must_have[name]
        prune_it = prune and dist not in smh
        if replace_existing or prune_it:
            add_unlink(actions, dist)

    return actions


def augment_specs(prefix, specs, pinned=True):
    # get conda-meta/pinned
    if pinned:
        pinned_specs = get_pinned_specs(prefix)
        log.debug("Pinned specs=%s", pinned_specs)
        specs += [MatchSpec(spec) for spec in pinned_specs]

    # support aggressive auto-update conda
    #   Only add a conda spec if conda and conda-env are not in the specs.
    #   Also skip this step if we're offline.
    root_only = ('conda', 'conda-env')
    mss = [MatchSpec(s) for s in specs if s.name.startswith(root_only)]
    mss = [ms for ms in mss if ms.name in root_only]
    if is_root_prefix(prefix):
        if context.auto_update_conda and not context.offline and not mss:
            specs.append(MatchSpec('conda'))
            specs.append(MatchSpec('conda-env'))
    elif basename(prefix).startswith('_'):
        # anything (including conda) can be installed into environments
        # starting with '_', mainly to allow conda-build to build conda
        pass
    elif mss:
        raise InstallError("Error: 'conda' can only be installed into the root environment")

    # support track_features config parameter
    if context.track_features:
        specs.extend(x + '@' for x in context.track_features)
    return specs


def remove_actions(prefix, specs, index, force=False, pinned=True):
    r = Resolve(index)
    linked = linked_data(prefix)
    linked_dists = [d for d in linked.keys()]

    if force:
        mss = list(map(MatchSpec, specs))
        nlinked = {r.package_name(dist): dist
                   for dist in linked_dists
                   if not any(r.match(ms, dist) for ms in mss)}
    else:
        add_defaults_to_specs(r, linked_dists, specs, update=True)
        nlinked = {r.package_name(dist): dist
                   for dist in (Dist(fn) for fn in r.remove(specs, r.installed))}

    if pinned:
        pinned_specs = get_pinned_specs(prefix)
        log.debug("Pinned specs=%s", pinned_specs)

    linked = {r.package_name(dist): dist for dist in linked_dists}

    actions = ensure_linked_actions(r.dependency_sort(nlinked), prefix)
    for old_dist in reversed(r.dependency_sort(linked)):
        # dist = old_fn + '.tar.bz2'
        name = r.package_name(old_dist)
        if old_dist == nlinked.get(name):
            continue
        if pinned and any(r.match(ms, old_dist) for ms in pinned_specs):
            msg = "Cannot remove %s because it is pinned. Use --no-pin to override."
            raise CondaRuntimeError(msg % old_dist.to_filename())
        if context.conda_in_root and name == 'conda' and name not in nlinked and not context.force:
            if any(s.split(' ', 1)[0] == 'conda' for s in specs):
                raise RemoveError("'conda' cannot be removed from the root environment")
            else:
                raise RemoveError("Error: this 'remove' command cannot be executed because it\n"
                                  "would require removing 'conda' dependencies")
        add_unlink(actions, old_dist)

    return actions


def remove_spec_action_from_prefix(prefix, dist):
    actions = defaultdict(list)
    actions[inst.PREFIX] = prefix
    actions['op_order'] = (inst.CHECK_FETCH, inst.RM_FETCHED, inst.FETCH, inst.CHECK_EXTRACT,
                           inst.RM_EXTRACTED, inst.EXTRACT,
                           inst.UNLINK, inst.LINK, inst.SYMLINK_CONDA)

    add_unlink(actions, dist)
    return actions


def revert_actions(prefix, revision=-1, index=None):
    # TODO: If revision raise a revision error, should always go back to a safe revision
    # change
    h = History(prefix)
    h.update()
    try:
        state = h.get_state(revision)
    except IndexError:
        raise CondaIndexError("no such revision: %d" % revision)

    curr = h.get_state()
    if state == curr:
        return {}

    dists = (Dist(s) for s in state)
    actions = ensure_linked_actions(dists, prefix)
    for dist in curr - state:
        add_unlink(actions, Dist(dist))

    # check whether it is a safe revision
    from .instructions import LINK, UNLINK, FETCH
    from .exceptions import CondaRevisionError
    for arg in set(actions.get(LINK, []) + actions.get(UNLINK, []) + actions.get(FETCH, [])):
        dist = Dist(arg)
        if dist not in index:
            msg = "Cannot revert to {}, since {} is not in repodata".format(revision, dist)
            raise CondaRevisionError(msg)

    return actions


# ---------------------------- EXECUTION --------------------------

def execute_actions(actions, index, verbose=False):
    plan = plan_from_actions(actions, index)
    with History(actions[PREFIX]):
        execute_instructions(plan, index, verbose)


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
            raise ArgumentError("The instruction '%s' takes at least"
                                " one argument" % line)

        instruction, arg = line.split(' ', 1)
        plan.append((instruction, arg))
    return plan


def execute_plan(old_plan, index=None, verbose=False):
    """
    Deprecated: This should `conda.instructions.execute_instructions` instead
    """
    plan = update_old_plan(old_plan)
    execute_instructions(plan, index, verbose)


if __name__ == '__main__':
    # for testing new revert_actions() only
    from pprint import pprint
    pprint(dict(revert_actions(sys.prefix, int(sys.argv[1]))))
