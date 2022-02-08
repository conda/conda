# -*- coding: utf-8 -*-
# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""
Handle the planning of installs and their execution.

NOTE:
    conda.install uses canonical package names in its interface functions,
    whereas conda.resolve uses package filenames, as those are used as index
    keys.  We try to keep fixes to this "impedance mismatch" local to this
    module.
"""
from __future__ import absolute_import, division, print_function, unicode_literals

from collections import defaultdict
from logging import getLogger
import sys

from ._vendor.boltons.setutils import IndexedSet
from ._vendor.toolz import concatv
from .base.constants import DEFAULTS_CHANNEL_NAME, UNKNOWN_CHANNEL
from .base.context import context, stack_context_default
from .common.compat import itervalues, text_type
from .common.io import env_vars, time_recorder
from .core.index import LAST_CHANNEL_URLS, _supplement_index_with_prefix
from .core.link import PrefixSetup, UnlinkLinkTransaction
from .core.solve import diff_for_unlink_link_precs
from .exceptions import CondaIndexError, PackagesNotFoundError
from .history import History
from .instructions import (FETCH, LINK, SYMLINK_CONDA, UNLINK)
from .models.channel import Channel, prioritize_channels
from .models.dist import Dist
from .models.enums import LinkType
from .models.match_spec import ChannelMatch
from .models.prefix_graph import PrefixGraph
from .models.records import PackageRecord
from .models.version import normalized_version
from .resolve import MatchSpec, dashlist
from .utils import human_bytes

log = getLogger(__name__)

# TODO: Remove conda/plan.py.  This module should be almost completely deprecated now.

def print_dists(dists_extras):
    fmt = "    %-27s|%17s"
    print(fmt % ('package', 'build'))
    print(fmt % ('-' * 27, '-' * 17))
    for prec, extra in dists_extras:
        line = fmt % (prec.name + '-' + prec.version, prec.build)
        if extra:
            line += extra
        print(line)


def display_actions(actions, index, show_channel_urls=None, specs_to_remove=(), specs_to_add=()):
    prefix = actions.get("PREFIX")
    builder = ['', '## Package Plan ##\n']
    if prefix:
        builder.append('  environment location: %s' % prefix)
        builder.append('')
    if specs_to_remove:
        builder.append('  removed specs: %s'
                       % dashlist(sorted(text_type(s) for s in specs_to_remove), indent=4))
        builder.append('')
    if specs_to_add:
        builder.append('  added / updated specs: %s'
                       % dashlist(sorted(text_type(s) for s in specs_to_add), indent=4))
        builder.append('')
    print('\n'.join(builder))

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
        for prec in actions[FETCH]:
            assert isinstance(prec, PackageRecord)
            extra = '%15s' % human_bytes(prec['size'])
            schannel = channel_filt(prec.channel.canonical_name)
            if schannel:
                extra += '  ' + schannel
            disp_lst.append((prec, extra))
        print_dists(disp_lst)

        if index and len(actions[FETCH]) > 1:
            num_bytes = sum(prec['size'] for prec in actions[FETCH])
            print(' ' * 4 + '-' * 60)
            print(" " * 43 + "Total: %14s" % human_bytes(num_bytes))

    # package -> [oldver-oldbuild, newver-newbuild]
    packages = defaultdict(lambda: list(('', '')))
    features = defaultdict(lambda: list(('', '')))
    channels = defaultdict(lambda: list(('', '')))
    records = defaultdict(lambda: list((None, None)))
    linktypes = {}

    for prec in actions.get(LINK, []):
        assert isinstance(prec, PackageRecord)
        pkg = prec['name']
        channels[pkg][1] = channel_str(prec)
        packages[pkg][1] = prec['version'] + '-' + prec['build']
        records[pkg][1] = prec
        linktypes[pkg] = LinkType.hardlink  # TODO: this is a lie; may have to give this report after UnlinkLinkTransaction.verify()  # NOQA
        features[pkg][1] = ','.join(prec.get('features') or ())
    for prec in actions.get(UNLINK, []):
        assert isinstance(prec, PackageRecord)
        pkg = prec['name']
        channels[pkg][0] = channel_str(prec)
        packages[pkg][0] = prec['version'] + '-' + prec['build']
        records[pkg][0] = prec
        features[pkg][0] = ','.join(prec.get('features') or ())

    new = {p for p in packages if not packages[p][0]}
    removed = {p for p in packages if not packages[p][1]}
    # New packages are actually listed in the left-hand column,
    # so let's move them over there
    for pkg in new:
        for var in (packages, features, channels, records):
            var[pkg] = var[pkg][::-1]

    updated = set()
    downgraded = set()
    channeled = set()
    oldfmt = {}
    newfmt = {}
    empty = True
    if packages:
        empty = False
        maxpkg = max(len(p) for p in packages) + 1
        maxoldver = max(len(p[0]) for p in packages.values())
        maxnewver = max(len(p[1]) for p in packages.values())
        maxoldfeatures = max(len(p[0]) for p in features.values())
        maxnewfeatures = max(len(p[1]) for p in features.values())
        maxoldchannels = max(len(channel_filt(p[0])) for p in channels.values())
        maxnewchannels = max(len(channel_filt(p[1])) for p in channels.values())
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
        print("\nThe following packages will be DOWNGRADED:\n")
        for pkg in sorted(downgraded):
            print(format(oldfmt[pkg] + arrow + newfmt[pkg], pkg))

    if empty and actions.get(SYMLINK_CONDA):
        print("\nThe following empty environments will be CREATED:\n")
        print(actions['PREFIX'])

    print('')


def add_unlink(actions, dist):
    assert isinstance(dist, Dist)
    if UNLINK not in actions:
        actions[UNLINK] = []
    actions[UNLINK].append(dist)


# -------------------------------------------------------------------


def add_defaults_to_specs(r, linked, specs, update=False, prefix=None):
    return


def _get_best_prec_match(precs):
    assert precs
    for chn in context.channels:
        channel_matcher = ChannelMatch(chn)
        prec_matches = tuple(prec for prec in precs if channel_matcher.match(prec.channel.name))
        if prec_matches:
            break
    else:
        prec_matches = precs
    log.warn("Multiple packages found:%s", dashlist(prec_matches))
    return prec_matches[0]


def revert_actions(prefix, revision=-1, index=None):
    # TODO: If revision raise a revision error, should always go back to a safe revision
    h = History(prefix)
    # TODO: need a History method to get user-requested specs for revision number
    #       Doing a revert right now messes up user-requested spec history.
    #       Either need to wipe out history after ``revision``, or add the correct
    #       history information to the new entry about to be created.
    # TODO: This is wrong!!!!!!!!!!
    user_requested_specs = itervalues(h.get_requested_specs_map())
    try:
        target_state = {MatchSpec.from_dist_str(dist_str) for dist_str in h.get_state(revision)}
    except IndexError:
        raise CondaIndexError("no such revision: %d" % revision)

    _supplement_index_with_prefix(index, prefix)

    not_found_in_index_specs = set()
    link_precs = set()
    for spec in target_state:
        precs = tuple(prec for prec in itervalues(index) if spec.match(prec))
        if not precs:
            not_found_in_index_specs.add(spec)
        elif len(precs) > 1:
            link_precs.add(_get_best_prec_match(precs))
        else:
            link_precs.add(precs[0])

    if not_found_in_index_specs:
        raise PackagesNotFoundError(not_found_in_index_specs)

    final_precs = IndexedSet(PrefixGraph(link_precs).graph)  # toposort
    unlink_precs, link_precs = diff_for_unlink_link_precs(prefix, final_precs)
    stp = PrefixSetup(prefix, unlink_precs, link_precs, (), user_requested_specs, ())
    txn = UnlinkLinkTransaction(stp)
    return txn


# ---------------------------- Backwards compat for conda-build --------------------------

@time_recorder("execute_actions")
def execute_actions(actions, index, verbose=False):  # pragma: no cover
    plan = _plan_from_actions(actions, index)
    execute_instructions(plan, index, verbose)


def _plan_from_actions(actions, index):  # pragma: no cover
    from .instructions import ACTION_CODES, PREFIX, PRINT, PROGRESS, PROGRESS_COMMANDS

    if 'op_order' in actions and actions['op_order']:
        op_order = actions['op_order']
    else:
        op_order = ACTION_CODES

    assert PREFIX in actions and actions[PREFIX]
    prefix = actions[PREFIX]
    plan = [('PREFIX', '%s' % prefix)]

    unlink_link_transaction = actions.get('UNLINKLINKTRANSACTION')
    if unlink_link_transaction:
        raise RuntimeError()
        # progressive_fetch_extract = actions.get('PROGRESSIVEFETCHEXTRACT')
        # if progressive_fetch_extract:
        #     plan.append((PROGRESSIVEFETCHEXTRACT, progressive_fetch_extract))
        # plan.append((UNLINKLINKTRANSACTION, unlink_link_transaction))
        # return plan

    axn = actions.get('ACTION') or None
    specs = actions.get('SPECS', [])

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

    plan = _inject_UNLINKLINKTRANSACTION(plan, index, prefix, axn, specs)

    return plan


def _inject_UNLINKLINKTRANSACTION(plan, index, prefix, axn, specs):  # pragma: no cover
    from os.path import isdir
    from .models.dist import Dist
    from ._vendor.toolz.itertoolz import groupby
    from .instructions import LINK, PROGRESSIVEFETCHEXTRACT, UNLINK, UNLINKLINKTRANSACTION
    from .core.package_cache_data import ProgressiveFetchExtract
    from .core.link import PrefixSetup, UnlinkLinkTransaction
    # this is only used for conda-build at this point
    first_unlink_link_idx = next((q for q, p in enumerate(plan) if p[0] in (UNLINK, LINK)), -1)
    if first_unlink_link_idx >= 0:
        grouped_instructions = groupby(lambda x: x[0], plan)
        unlink_dists = tuple(Dist(d[1]) for d in grouped_instructions.get(UNLINK, ()))
        link_dists = tuple(Dist(d[1]) for d in grouped_instructions.get(LINK, ()))
        unlink_dists, link_dists = _handle_menuinst(unlink_dists, link_dists)

        if isdir(prefix):
            unlink_precs = tuple(index[d] for d in unlink_dists)
        else:
            # there's nothing to unlink in an environment that doesn't exist
            # this is a hack for what appears to be a logic error in conda-build
            # caught in tests/test_subpackages.py::test_subpackage_recipes[python_test_dep]
            unlink_precs = ()
        link_precs = tuple(index[d] for d in link_dists)

        pfe = ProgressiveFetchExtract(link_precs)
        pfe.prepare()

        stp = PrefixSetup(prefix, unlink_precs, link_precs, (), specs, ())
        plan.insert(first_unlink_link_idx, (UNLINKLINKTRANSACTION, UnlinkLinkTransaction(stp)))
        plan.insert(first_unlink_link_idx, (PROGRESSIVEFETCHEXTRACT, pfe))
    elif axn in ('INSTALL', 'CREATE'):
        plan.insert(0, (UNLINKLINKTRANSACTION, (prefix, (), (), (), specs)))

    return plan


def _handle_menuinst(unlink_dists, link_dists):  # pragma: no cover
    from .common.compat import on_win
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


@time_recorder("install_actions")
def install_actions(prefix, index, specs, force=False, only_names=None, always_copy=False,
                    pinned=True, update_deps=True, prune=False,
                    channel_priority_map=None, is_update=False,
                    minimal_hint=False):  # pragma: no cover
    # this is for conda-build
    with env_vars({
        'CONDA_ALLOW_NON_CHANNEL_URLS': 'true',
        'CONDA_SOLVER_IGNORE_TIMESTAMPS': 'false',
    }, stack_callback=stack_context_default):
        from os.path import basename
        from ._vendor.boltons.setutils import IndexedSet
        from .core.solve import _get_solver_class
        from .models.channel import Channel
        from .models.dist import Dist
        if channel_priority_map:
            channel_names = IndexedSet(Channel(url).canonical_name for url in channel_priority_map)
            channels = IndexedSet(Channel(cn) for cn in channel_names)
            subdirs = IndexedSet(basename(url) for url in channel_priority_map)
        else:
            # a hack for when conda-build calls this function without giving channel_priority_map
            if LAST_CHANNEL_URLS:
                channel_priority_map = prioritize_channels(LAST_CHANNEL_URLS)
                channels = IndexedSet(Channel(url) for url in channel_priority_map)
                subdirs = IndexedSet(
                    subdir for subdir in (c.subdir for c in channels) if subdir
                ) or context.subdirs
            else:
                channels = subdirs = None

        specs = tuple(MatchSpec(spec) for spec in specs)

        from .core.prefix_data import PrefixData
        PrefixData._cache_.clear()

        solver = _get_solver_class()(prefix, channels, subdirs, specs_to_add=specs)
        if index:
            solver._index = {prec: prec for prec in itervalues(index)}
        txn = solver.solve_for_transaction(prune=prune, ignore_pinned=not pinned)
        prefix_setup = txn.prefix_setups[prefix]
        actions = get_blank_actions(prefix)
        actions['UNLINK'].extend(Dist(prec) for prec in prefix_setup.unlink_precs)
        actions['LINK'].extend(Dist(prec) for prec in prefix_setup.link_precs)
        return actions


def get_blank_actions(prefix):  # pragma: no cover
    from collections import defaultdict
    from .instructions import (CHECK_EXTRACT, CHECK_FETCH, EXTRACT, FETCH, LINK, PREFIX,
                               RM_EXTRACTED, RM_FETCHED, SYMLINK_CONDA, UNLINK)
    actions = defaultdict(list)
    actions[PREFIX] = prefix
    actions['op_order'] = (CHECK_FETCH, RM_FETCHED, FETCH, CHECK_EXTRACT,
                           RM_EXTRACTED, EXTRACT,
                           UNLINK, LINK, SYMLINK_CONDA)
    return actions


@time_recorder("execute_plan")
def execute_plan(old_plan, index=None, verbose=False):  # pragma: no cover
    """
    Deprecated: This should `conda.instructions.execute_instructions` instead
    """
    plan = _update_old_plan(old_plan)
    execute_instructions(plan, index, verbose)


def execute_instructions(plan, index=None, verbose=False, _commands=None):  # pragma: no cover
    """Execute the instructions in the plan

    :param plan: A list of (instruction, arg) tuples
    :param index: The meta-data index
    :param verbose: verbose output
    :param _commands: (For testing only) dict mapping an instruction to executable if None
    then the default commands will be used
    """
    from .instructions import commands, PROGRESS_COMMANDS
    from .base.context import context
    from .models.dist import Dist
    if _commands is None:
        _commands = commands

    log.debug("executing plan %s", plan)

    state = {'i': None, 'prefix': context.root_prefix, 'index': index}

    for instruction, arg in plan:

        log.debug(' %s(%r)', instruction, arg)

        if state['i'] is not None and instruction in PROGRESS_COMMANDS:
            state['i'] += 1
            getLogger('progress.update').info((Dist(arg).dist_name,
                                               state['i'] - 1))
        cmd = _commands[instruction]

        if callable(cmd):
            cmd(state, arg)

        if (state['i'] is not None and instruction in PROGRESS_COMMANDS
                and state['maxval'] == state['i']):

            state['i'] = None
            getLogger('progress.stop').info(None)


def _update_old_plan(old_plan):  # pragma: no cover
    """
    Update an old plan object to work with
    `conda.instructions.execute_instructions`
    """
    plan = []
    for line in old_plan:
        if line.startswith('#'):
            continue
        if ' ' not in line:
            from .exceptions import ArgumentError
            raise ArgumentError("The instruction '%s' takes at least"
                                " one argument" % line)

        instruction, arg = line.split(' ', 1)
        plan.append((instruction, arg))
    return plan


if __name__ == '__main__':
    # for testing new revert_actions() only
    from pprint import pprint
    pprint(dict(revert_actions(sys.prefix, int(sys.argv[1]))))
