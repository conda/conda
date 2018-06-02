# -*- coding: utf-8 -*-
# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
from __future__ import absolute_import, division, print_function, unicode_literals

from collections import Hashable
from logging import getLogger
import threading
from warnings import warn

log = getLogger(__name__)

from . import CondaError  # NOQA
CondaError = CondaError

from .base.context import reset_context  # NOQA
reset_context()  # initialize context when conda.exports is imported

from . import compat, plan  # NOQA
compat, plan = compat, plan

from .core.solve import Solver  # NOQA
Solver = Solver

from .cli.common import specs_from_args, spec_from_line, specs_from_url  # NOQA
from .cli.conda_argparse import add_parser_prefix, add_parser_channels  # NOQA
add_parser_channels, add_parser_prefix = add_parser_channels, add_parser_prefix
specs_from_args, spec_from_line = specs_from_args, spec_from_line
specs_from_url = specs_from_url

from .cli.conda_argparse import ArgumentParser  # NOQA
ArgumentParser = ArgumentParser

from .common.compat import PY3, StringIO, input, iteritems, string_types, text_type, \
    itervalues  # NOQA
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
from .core.package_cache_data import download, rm_fetched  # NOQA
download, rm_fetched = download, rm_fetched

from .install import package_cache, prefix_placeholder, symlink_conda  # NOQA
package_cache, prefix_placeholder, symlink_conda = package_cache, prefix_placeholder, symlink_conda

from .gateways.disk.delete import delete_trash, move_to_trash  # NOQA
delete_trash, move_to_trash = delete_trash, move_to_trash

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
VersionOrder, normalized_version = VersionOrder, normalized_version  # NOQA

import conda.base.context  # NOQA
from .base.context import get_prefix, non_x86_linux_machines, reset_context, sys_rc_path  # NOQA
non_x86_linux_machines, sys_rc_path = non_x86_linux_machines, sys_rc_path
get_prefix = get_prefix
reset_context = reset_context

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
conda_build = conda.base.context.context.conda_build
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

from .models.records import PackageRecord  # NOQA
PackageRecord = IndexRecord = PackageRecord

from .models.dist import Dist  # NOQA
Dist = Dist

from .compat import TemporaryDirectory  # NOQA
TemporaryDirectory = TemporaryDirectory

from .gateways.subprocess import ACTIVE_SUBPROCESSES, subprocess_call  # NOQA
ACTIVE_SUBPROCESSES, subprocess_call = ACTIVE_SUBPROCESSES, subprocess_call

from .core.subdir_data import cache_fn_url  # NOQA
cache_fn_url = cache_fn_url

from .core.package_cache_data import ProgressiveFetchExtract  # NOQA
ProgressiveFetchExtract = ProgressiveFetchExtract


from .exceptions import CondaHTTPError, LinkError, LockError, NoPackagesFoundError, PaddingError  # NOQA
from .exceptions import UnsatisfiableError  # NOQA
CondaHTTPError, LinkError, LockError = CondaHTTPError, LinkError, LockError
NoPackagesFoundError, PaddingError = NoPackagesFoundError, PaddingError
UnsatisfiableError = UnsatisfiableError


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
from .core.prefix_data import delete_prefix_from_linked_data  # NOQA


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


from .plan import execute_actions, execute_instructions, execute_plan, install_actions  # NOQA
execute_actions, execute_instructions = execute_actions, execute_instructions
execute_plan, install_actions = execute_plan, install_actions


from .install import linked_data, linked, is_linked  # NOQA
linked_data, linked, is_linked = linked_data, linked, is_linked


from .plan import display_actions as _display_actions  # NOQA
def display_actions(actions, index, show_channel_urls=None, specs_to_remove=(), specs_to_add=()):
    if 'FETCH' in actions:
        actions['FETCH'] = [index[d] for d in actions['FETCH']]
    if 'LINK' in actions:
        actions['LINK'] = [index[d] for d in actions['LINK']]
    if 'UNLINK' in actions:
        actions['UNLINK'] = [index[d] for d in actions['UNLINK']]
    index = {prec: prec for prec in itervalues(index)}
    return _display_actions(actions, index, show_channel_urls, specs_to_remove, specs_to_add)


from .models.dist import Dist  # NOQA
from .core.index import dist_str_in_index, fetch_index as _fetch_index, get_index as _get_index  # NOQA
dist_str_in_index = dist_str_in_index


def get_index(channel_urls=(), prepend=True, platform=None,
              use_local=False, use_cache=False, unknown=None, prefix=None):
    index = _get_index(channel_urls, prepend, platform, use_local, use_cache, unknown, prefix)
    return {Dist(prec): prec for prec in itervalues(index)}


def fetch_index(channel_urls, use_cache=False, index=None):
    index = _fetch_index(channel_urls, use_cache, index)
    return {Dist(prec): prec for prec in itervalues(index)}
