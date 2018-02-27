# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function, unicode_literals

from collections import Hashable
from logging import getLogger
import threading
from warnings import warn

log = getLogger(__name__)

from . import CondaError  # NOQA
CondaError = CondaError  # lgtm [py/redundant-assignment]

from . import compat, plan  # NOQA
compat, plan = compat, plan

from .core.solve import Solver  # NOQA
Solver = Solver  # lgtm [py/redundant-assignment]

from .plan import display_actions  # NOQA
display_actions = display_actions  # lgtm [py/redundant-assignment]

from .cli.common import specs_from_args, spec_from_line, specs_from_url  # NOQA
from .cli.conda_argparse import add_parser_prefix, add_parser_channels  # NOQA
add_parser_channels, add_parser_prefix = add_parser_channels, add_parser_prefix
specs_from_args, spec_from_line = specs_from_args, spec_from_line
specs_from_url = specs_from_url  # lgtm [py/redundant-assignment]

from .cli.conda_argparse import ArgumentParser  # NOQA
ArgumentParser = ArgumentParser  # lgtm [py/redundant-assignment]

from .common.compat import PY3, StringIO,  input, iteritems, string_types, text_type  # NOQA
PY3, StringIO,  input, iteritems, string_types, text_type = PY3, StringIO,  input, iteritems, string_types, text_type  # NOQA lgtm [py/redundant-assignment]
from .gateways.connection.session import CondaSession  # NOQA
CondaSession = CondaSession  # lgtm [py/redundant-assignment]

from .common.toposort import _toposort  # NOQA
_toposort = _toposort  # lgtm [py/redundant-assignment]

from .gateways.disk.link import lchmod  # NOQA
lchmod = lchmod  # lgtm [py/redundant-assignment]

from .gateways.connection.download import TmpDownload  # NOQA

TmpDownload = TmpDownload  # lgtm [py/redundant-assignment]
handle_proxy_407 = lambda x, y: warn("handle_proxy_407 is deprecated. "
                                     "Now handled by CondaSession.")
from .core.index import dist_str_in_index, fetch_index, get_index  # NOQA
dist_str_in_index, fetch_index, get_index = dist_str_in_index, fetch_index, get_index  # NOQA lgtm [py/redundant-assignment]
from .core.package_cache_data import download, rm_fetched  # NOQA
download, rm_fetched = download, rm_fetched

from .install import package_cache, prefix_placeholder, symlink_conda  # NOQA
package_cache, prefix_placeholder, symlink_conda = package_cache, prefix_placeholder, symlink_conda

from .gateways.disk.delete import delete_trash, move_to_trash  # NOQA
delete_trash, move_to_trash = delete_trash, move_to_trash

from .core.prefix_data import is_linked, linked, linked_data  # NOQA
is_linked, linked, linked_data = is_linked, linked, linked_data

from .misc import untracked, walk_prefix  # NOQA
untracked, walk_prefix = untracked, walk_prefix

from .resolve import MatchSpec, ResolvePackageNotFound, Resolve, Unsatisfiable  # NOQA
MatchSpec, Resolve = MatchSpec, Resolve
Unsatisfiable = Unsatisfiable  # lgtm [py/redundant-assignment]
NoPackagesFound = NoPackagesFoundError = ResolvePackageNotFound  # lgtm [py/redundant-assignment]

from .utils import hashsum_file, human_bytes, unix_path_to_win, url_path  # NOQA
from .common.path import win_path_to_unix  # NOQA
hashsum_file, human_bytes = hashsum_file, human_bytes
unix_path_to_win = unix_path_to_win  # lgtm [py/redundant-assignment]
win_path_to_unix, url_path = win_path_to_unix, url_path

from .gateways.disk.read import compute_md5sum  # NOQA
md5_file = compute_md5sum  # lgtm [py/redundant-assignment]

from .models.version import VersionOrder, normalized_version  # NOQA
VersionOrder, normalized_version = VersionOrder, normalized_version  # NOQA lgtm [py/redundant-assignment]

import conda.base.context  # NOQA
from .base.context import get_prefix, non_x86_linux_machines, sys_rc_path  # NOQA
non_x86_linux_machines, sys_rc_path = non_x86_linux_machines, sys_rc_path
get_prefix = get_prefix  # lgtm [py/redundant-assignment]

from ._vendor.auxlib.entity import EntityEncoder # NOQA
EntityEncoder = EntityEncoder  # lgtm [py/redundant-assignment]
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
PaddingError = PaddingError  # lgtm [py/redundant-assignment]
LinkError = LinkError  # lgtm [py/redundant-assignment]
CondaOSError = CondaOSError  # lgtm [py/redundant-assignment]
# PathNotFoundError is the conda 4.4.x name for it - let's plan ahead.
PathNotFoundError = CondaFileNotFoundError = PathNotFoundError  # lgtm [py/redundant-assignment]
from .gateways.disk.link import CrossPlatformStLink  # NOQA
CrossPlatformStLink = CrossPlatformStLink  # lgtm [py/redundant-assignment]

from .models.enums import FileMode  # NOQA
FileMode = FileMode  # lgtm [py/redundant-assignment]
from .models.enums import PathType  # NOQA
PathType = PathType  # lgtm [py/redundant-assignment]

from .models.records import PackageRecord
PackageRecord = IndexRecord = PackageRecord

from .compat import TemporaryDirectory  # NOQA
TemporaryDirectory = TemporaryDirectory  # lgtm [py/redundant-assignment]

from .gateways.subprocess import ACTIVE_SUBPROCESSES, subprocess_call  # NOQA
ACTIVE_SUBPROCESSES, subprocess_call = ACTIVE_SUBPROCESSES, subprocess_call

from .core.subdir_data import cache_fn_url  # NOQA
cache_fn_url = cache_fn_url  # lgtm [py/redundant-assignment]


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
