# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function, unicode_literals

from collections import Hashable
from logging import getLogger
import threading
from warnings import warn

log = getLogger(__name__)

from . import CondaError  # NOQA
CondaError = CondaError

from . import compat, plan  # NOQA
compat, plan = compat, plan

from .core.solve import Solver  # NOQA
Solver = Solver

from .plan import display_actions  # NOQA
display_actions = display_actions

from .cli.common import specs_from_args, spec_from_line, specs_from_url  # NOQA
from .cli.conda_argparse import add_parser_prefix, add_parser_channels  # NOQA
add_parser_channels, add_parser_prefix = add_parser_channels, add_parser_prefix
specs_from_args, spec_from_line = specs_from_args, spec_from_line
specs_from_url = specs_from_url

from .cli.conda_argparse import ArgumentParser  # NOQA
ArgumentParser = ArgumentParser

from .common.compat import PY3, StringIO,  input, iteritems, string_types, text_type  # NOQA
PY3, StringIO,  input, iteritems, string_types, text_type = PY3, StringIO,  input, iteritems, string_types, text_type  # NOQA
from .gateways.connection.session import CondaSession  # NOQA
CondaSession = CondaSession

from .common.toposort import _toposort  # NOQA
_toposort = _toposort

from .gateways.disk.link import lchmod  # NOQA
lchmod = lchmod

from .gateways.connection.download import TmpDownload  # NOQA

TmpDownload = TmpDownload
handle_proxy_407 = lambda x, y: warn("handle_proxy_407 is deprecated. "
                                     "Now handled by CondaSession.")
from .core.index import dist_str_in_index, fetch_index, get_index  # NOQA
dist_str_in_index, fetch_index, get_index = dist_str_in_index, fetch_index, get_index
from .core.package_cache import download, rm_fetched  # NOQA
download, rm_fetched = download, rm_fetched

from .install import package_cache, prefix_placeholder, symlink_conda  # NOQA
package_cache, prefix_placeholder, symlink_conda = package_cache, prefix_placeholder, symlink_conda  # NOQA

from .gateways.disk.delete import delete_trash, move_to_trash  # NOQA
delete_trash, move_to_trash = delete_trash, move_to_trash

from .core.linked_data import is_linked, linked, linked_data  # NOQA
is_linked, linked, linked_data = is_linked, linked, linked_data

from .misc import untracked, walk_prefix  # NOQA
untracked, walk_prefix = untracked, walk_prefix

from .resolve import MatchSpec, ResolvePackageNotFound, Resolve, Unsatisfiable  # NOQA
MatchSpec, Resolve = MatchSpec, Resolve
Unsatisfiable = Unsatisfiable
NoPackagesFound = NoPackagesFoundError = ResolvePackageNotFound

from .utils import hashsum_file, human_bytes, unix_path_to_win, url_path  # NOQA
from .common.path import win_path_to_unix  # NOQA
hashsum_file, human_bytes = hashsum_file, human_bytes
unix_path_to_win = unix_path_to_win
win_path_to_unix, url_path = win_path_to_unix, url_path

from .gateways.disk.read import compute_md5sum  # NOQA
md5_file = compute_md5sum

from .models.version import VersionOrder, normalized_version  # NOQA
VersionOrder, normalized_version = VersionOrder, normalized_version

import conda.base.context  # NOQA
from .base.context import get_prefix, non_x86_linux_machines, sys_rc_path  # NOQA
non_x86_linux_machines, sys_rc_path = non_x86_linux_machines, sys_rc_path
get_prefix = get_prefix

from ._vendor.auxlib.entity import EntityEncoder # NOQA
EntityEncoder = EntityEncoder
from .base.constants import DEFAULT_CHANNELS, DEFAULT_CHANNELS_WIN, DEFAULT_CHANNELS_UNIX  # NOQA
DEFAULT_CHANNELS, DEFAULT_CHANNELS_WIN, DEFAULT_CHANNELS_UNIX = DEFAULT_CHANNELS, DEFAULT_CHANNELS_WIN, DEFAULT_CHANNELS_UNIX  # NOQA
get_default_urls = lambda: DEFAULT_CHANNELS

arch_name = conda.base.context.context.arch_name
binstar_upload = conda.base.context.context.anaconda_upload
bits = conda.base.context.context.bits
default_prefix = conda.base.context.context.default_prefix
default_python = conda.base.context.context.default_python
envs_dirs = conda.base.context.context.envs_dirs
pkgs_dirs = conda.base.context.context.pkgs_dirs
platform = conda.base.context.context.platform
root_dir = conda.base.context.context.root_prefix
root_writable = conda.base.context.context.root_writable
subdir = conda.base.context.context.subdir
conda_private = conda.base.context.context.conda_private
from .models.channel import get_conda_build_local_url  # NOQA
get_rc_urls = lambda: list(conda.base.context.context.channels)
get_local_urls = lambda: list(get_conda_build_local_url()) or []
load_condarc = lambda fn: conda.base.context.reset_context([fn])
from .exceptions import PaddingError, LinkError, CondaOSError, PathNotFoundError  # NOQA
PaddingError = PaddingError
LinkError = LinkError
CondaOSError = CondaOSError
# PathNotFoundError is the conda 4.4.x name for it - let's plan ahead.
PathNotFoundError = CondaFileNotFoundError = PathNotFoundError
from .gateways.disk.link import CrossPlatformStLink  # NOQA
CrossPlatformStLink = CrossPlatformStLink

from .models.enums import FileMode  # NOQA
FileMode = FileMode
from .models.enums import PathType  # NOQA
PathType = PathType

from .compat import TemporaryDirectory  # NOQA
TemporaryDirectory = TemporaryDirectory

from .gateways.subprocess import ACTIVE_SUBPROCESSES, subprocess_call  # NOQA
ACTIVE_SUBPROCESSES, subprocess_call = ACTIVE_SUBPROCESSES, subprocess_call

from .core.repodata import cache_fn_url  # NOQA
cache_fn_url = cache_fn_url


class Completer(object):  # pragma: no cover
    def get_items(self):
        return self._get_items()

    def __contains__(self, item):
        return True

    def __iter__(self):
        return iter(self.get_items())


class InstalledPackages(object):
    pass


class memoized(object):  # pragma: no cover
    """Decorator. Caches a function's return value each time it is called.
    If called later with the same arguments, the cached value is returned
    (not reevaluated).
    """
    def __init__(self, func):
        self.func = func
        self.cache = {}
        self.lock = threading.Lock()

    def __call__(self, *args, **kw):
        newargs = []
        for arg in args:
            if isinstance(arg, list):
                newargs.append(tuple(arg))
            elif not isinstance(arg, Hashable):
                # uncacheable. a list, for instance.
                # better to not cache than blow up.
                return self.func(*args, **kw)
            else:
                newargs.append(arg)
        newargs = tuple(newargs)
        key = (newargs, frozenset(sorted(kw.items())))
        with self.lock:
            if key in self.cache:
                return self.cache[key]
            else:
                value = self.func(*args, **kw)
                self.cache[key] = value
                return value


from .gateways.disk.delete import rm_rf as _rm_rf  # NOQA
from .core.linked_data import delete_prefix_from_linked_data  # NOQA


def rm_rf(path, max_retries=5, trash=True):
    _rm_rf(path, max_retries, trash)
    delete_prefix_from_linked_data(path)


# ######################
# signature.py
# ######################
KEYS = None
KEYS_DIR = None


def hash_file(_):
    return None  # pragma: no cover


def verify(_):
    return False  # pragma: no cover


def execute_actions(actions, index, verbose=False):
    plan = _plan_from_actions(actions, index)
    execute_instructions(plan, index, verbose)


def _plan_from_actions(actions, index):
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


def _inject_UNLINKLINKTRANSACTION(plan, index, prefix, axn, specs):
    from os.path import isdir
    from .models.dist import Dist
    from ._vendor.toolz.itertoolz import groupby
    from .instructions import LINK, PROGRESSIVEFETCHEXTRACT, UNLINK, UNLINKLINKTRANSACTION
    from .core.package_cache import ProgressiveFetchExtract
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

        stp = PrefixSetup(prefix, unlink_precs, link_precs, (), specs)
        plan.insert(first_unlink_link_idx, (UNLINKLINKTRANSACTION, UnlinkLinkTransaction(stp)))
        plan.insert(first_unlink_link_idx, (PROGRESSIVEFETCHEXTRACT, pfe))
    elif axn in ('INSTALL', 'CREATE'):
        plan.insert(0, (UNLINKLINKTRANSACTION, (prefix, (), (), (), specs)))

    return plan


def _handle_menuinst(unlink_dists, link_dists):
    from ._vendor.toolz.itertoolz import concatv
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


def install_actions(prefix, index, specs, force=False, only_names=None, always_copy=False,
                    pinned=True, update_deps=True, prune=False,
                    channel_priority_map=None, is_update=False,
                    minimal_hint=False):  # pragma: no cover
    # this is for conda-build
    from os.path import basename
    from ._vendor.boltons.setutils import IndexedSet
    from .models.channel import Channel
    from .models.dist import Dist
    if channel_priority_map:
        channel_names = IndexedSet(Channel(url).canonical_name for url in channel_priority_map)
        channels = IndexedSet(Channel(cn) for cn in channel_names)
        subdirs = IndexedSet(basename(url) for url in channel_priority_map)
    else:
        channels = subdirs = None

    specs = tuple(MatchSpec(spec) for spec in specs)

    from .core.linked_data import PrefixData
    PrefixData._cache_.clear()

    solver = Solver(prefix, channels, subdirs, specs_to_add=specs)
    if index:
        solver._index = index
    txn = solver.solve_for_transaction(prune=prune, ignore_pinned=not pinned)
    prefix_setup = txn.prefix_setups[prefix]
    actions = get_blank_actions(prefix)
    actions['UNLINK'].extend(Dist(prec) for prec in prefix_setup.unlink_precs)
    actions['LINK'].extend(Dist(prec) for prec in prefix_setup.link_precs)
    return actions


def get_blank_actions(prefix):
    from collections import defaultdict
    from .instructions import (CHECK_EXTRACT, CHECK_FETCH, EXTRACT, FETCH, LINK, PREFIX,
                               RM_EXTRACTED, RM_FETCHED, SYMLINK_CONDA, UNLINK)
    actions = defaultdict(list)
    actions[PREFIX] = prefix
    actions['op_order'] = (CHECK_FETCH, RM_FETCHED, FETCH, CHECK_EXTRACT,
                           RM_EXTRACTED, EXTRACT,
                           UNLINK, LINK, SYMLINK_CONDA)
    return actions


def execute_plan(old_plan, index=None, verbose=False):
    """
    Deprecated: This should `conda.instructions.execute_instructions` instead
    """
    plan = _update_old_plan(old_plan)
    execute_instructions(plan, index, verbose)


def execute_instructions(plan, index=None, verbose=False, _commands=None):
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

        if (state['i'] is not None and instruction in PROGRESS_COMMANDS and
                state['maxval'] == state['i']):

            state['i'] = None
            getLogger('progress.stop').info(None)


def _update_old_plan(old_plan):
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
