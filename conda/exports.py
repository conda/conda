# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function, unicode_literals

from functools import partial
from logging import getLogger
from warnings import warn

log = getLogger(__name__)

from . import CondaError  # NOQA
CondaError = CondaError

from . import compat, plan  # NOQA
compat, plan = compat, plan

from .api import get_index  # NOQA
get_index = get_index

from .cli.common import (Completer, InstalledPackages, add_parser_channels, add_parser_prefix,  # NOQA
                              specs_from_args, spec_from_line, specs_from_url)  # NOQA
Completer, InstalledPackages = Completer, InstalledPackages
add_parser_channels, add_parser_prefix = add_parser_channels, add_parser_prefix
specs_from_args, spec_from_line = specs_from_args, spec_from_line
specs_from_url = specs_from_url

from .cli.conda_argparse import ArgumentParser  # NOQA
ArgumentParser = ArgumentParser

from .common.compat import PY3, StringIO,  input, iteritems, string_types, text_type  # NOQA
PY3, StringIO,  input, iteritems, string_types, text_type = PY3, StringIO,  input, iteritems, string_types, text_type  # NOQA
from .connection import CondaSession  # NOQA
CondaSession = CondaSession

from .gateways.disk.link import lchmod  # NOQA
lchmod = lchmod

from .fetch import TmpDownload  # NOQA
TmpDownload = TmpDownload
handle_proxy_407 = lambda x, y: warn("handle_proxy_407 is deprecated. "
                                     "Now handled by CondaSession.")
from .core.index import dist_str_in_index, fetch_index  # NOQA
dist_str_in_index, fetch_index = dist_str_in_index, fetch_index
from .core.package_cache import download, rm_fetched  # NOQA
download, rm_fetched = download, rm_fetched

from .install import package_cache, prefix_placeholder, rm_rf, symlink_conda  # NOQA
package_cache, prefix_placeholder, rm_rf, symlink_conda = package_cache, prefix_placeholder, rm_rf, symlink_conda  # NOQA

from .gateways.disk.delete import delete_trash, move_to_trash  # NOQA
delete_trash, move_to_trash = delete_trash, move_to_trash

from .core.linked_data import is_linked, linked, linked_data  # NOQA
is_linked, linked, linked_data = is_linked, linked, linked_data

from .misc import untracked, walk_prefix  # NOQA
untracked, walk_prefix = untracked, walk_prefix

from .resolve import MatchSpec, NoPackagesFound, Resolve, Unsatisfiable, normalized_version  # NOQA
MatchSpec, NoPackagesFound, Resolve = MatchSpec, NoPackagesFound, Resolve
Unsatisfiable, normalized_version = Unsatisfiable, normalized_version

from .signature import KEYS, KEYS_DIR, hash_file, verify  # NOQA
KEYS, KEYS_DIR = KEYS, KEYS_DIR
hash_file, verify = hash_file, verify

from .utils import (human_bytes, hashsum_file, md5_file, memoized, unix_path_to_win,  # NOQA
                         win_path_to_unix, url_path)  # NOQA
human_bytes, hashsum_file, md5_file = human_bytes, hashsum_file, md5_file
memoized, unix_path_to_win = memoized, unix_path_to_win
win_path_to_unix, url_path = win_path_to_unix, url_path

from .config import sys_rc_path  # NOQA
sys_rc_path = sys_rc_path

from .version import VersionOrder  # NOQA
VersionOrder = VersionOrder


import conda.base.context  # NOQA
from conda.base.context import get_prefix as context_get_prefix, non_x86_linux_machines  # NOQA
non_x86_linux_machines = non_x86_linux_machines

from ._vendor.auxlib.entity import EntityEncoder        # NOQA
EntityEncoder = EntityEncoder
from .base.constants import DEFAULT_CHANNELS, DEFAULT_CHANNELS_WIN, DEFAULT_CHANNELS_UNIX  # NOQA
DEFAULT_CHANNELS, DEFAULT_CHANNELS_WIN, DEFAULT_CHANNELS_UNIX = DEFAULT_CHANNELS, DEFAULT_CHANNELS_WIN, DEFAULT_CHANNELS_UNIX  # NOQA
get_prefix = partial(context_get_prefix, conda.base.context.context)
get_default_urls = lambda: DEFAULT_CHANNELS

arch_name = conda.base.context.context.arch_name
binstar_upload = conda.base.context.context.binstar_upload
bits = conda.base.context.context.bits
default_prefix = conda.base.context.context.default_prefix
default_python = conda.base.context.context.default_python
envs_dirs = conda.base.context.context.envs_dirs
pkgs_dirs = conda.base.context.context.pkgs_dirs
platform = conda.base.context.context.platform
root_dir = conda.base.context.context.root_prefix
root_writable = conda.base.context.context.root_writable
subdir = conda.base.context.context.subdir
from .models.channel import get_conda_build_local_url  # NOQA
get_rc_urls = lambda: list(conda.base.context.context.channels)
get_local_urls = lambda: list(get_conda_build_local_url()) or []
load_condarc = lambda fn: conda.base.context.reset_context([fn])
from .exceptions import PaddingError  # NOQA
PaddingError = PaddingError
from .gateways.disk.link import CrossPlatformStLink  # NOQA
CrossPlatformStLink = CrossPlatformStLink

from .models.enums import FileMode  # NOQA
FileMode = FileMode
from .models.enums import PathType  # NOQA
PathType = PathType


if PY3:
    import configparser  # NOQA  # pragma: py2 no cover
else:
    import ConfigParser as configparser  # NOQA  # pragma: py3 no cover
configparser = configparser


from .compat import TemporaryDirectory  # NOQA
TemporaryDirectory = TemporaryDirectory

from .gateways.subprocess import ACTIVE_SUBPROCESSES, subprocess_call  # NOQA
ACTIVE_SUBPROCESSES, subprocess_call = ACTIVE_SUBPROCESSES, subprocess_call
