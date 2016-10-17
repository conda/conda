# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function, unicode_literals

from functools import partial
from warnings import warn

from conda import compat, plan
compat = compat
plan = plan

from conda.api import get_index  # NOQA
get_index = get_index

from conda.cli.common import (Completer, InstalledPackages, add_parser_channels, add_parser_prefix,  # NOQA
                              specs_from_args, spec_from_line, specs_from_url)  # NOQA
Completer, InstalledPackages = Completer, InstalledPackages
add_parser_channels, add_parser_prefix = add_parser_channels, add_parser_prefix
specs_from_args, spec_from_line = specs_from_args, spec_from_line
specs_from_url = specs_from_url

from conda.cli.conda_argparse import ArgumentParser  # NOQA
ArgumentParser = ArgumentParser

from conda.compat import (PY3, StringIO, configparser, input, iteritems, lchmod, string_types,  # NOQA
                          text_type, TemporaryDirectory)  # NOQA
PY3, StringIO, configparser, input = PY3, StringIO, configparser, input
iteritems, lchmod, string_types = iteritems, lchmod, string_types
text_type, TemporaryDirectory = text_type, TemporaryDirectory

from conda.connection import CondaSession  # NOQA
CondaSession = CondaSession

from conda.fetch import TmpDownload, download, fetch_index  # NOQA
TmpDownload, download, fetch_index = TmpDownload, download, fetch_index
handle_proxy_407 = lambda x, y: warn("handle_proxy_407 is deprecated. "
                                     "Now handled by CondaSession.")

from conda.install import (delete_trash, is_linked, linked, linked_data, move_to_trash,  # NOQA
                           prefix_placeholder, rm_rf, symlink_conda, rm_fetched, package_cache)  # NOQA
delete_trash, is_linked, linked = delete_trash, is_linked, linked
linked_data, move_to_trash = linked_data, move_to_trash
prefix_placeholder, rm_rf, symlink_conda = prefix_placeholder, rm_rf, symlink_conda
rm_fetched, package_cache = rm_fetched, package_cache

from conda.lock import Locked  # NOQA
Locked = Locked

from conda.misc import untracked, walk_prefix  # NOQA
untracked, walk_prefix = untracked, walk_prefix

from conda.resolve import MatchSpec, NoPackagesFound, Resolve, Unsatisfiable, normalized_version  # NOQA
MatchSpec, NoPackagesFound, Resolve = MatchSpec, NoPackagesFound, Resolve
Unsatisfiable, normalized_version = Unsatisfiable, normalized_version

from conda.signature import KEYS, KEYS_DIR, hash_file, verify  # NOQA
KEYS, KEYS_DIR = KEYS, KEYS_DIR
hash_file, verify = hash_file, verify

from conda.utils import (human_bytes, hashsum_file, md5_file, memoized, unix_path_to_win,  # NOQA
                         win_path_to_unix, url_path)  # NOQA
human_bytes, hashsum_file, md5_file = human_bytes, hashsum_file, md5_file
memoized, unix_path_to_win = memoized, unix_path_to_win
win_path_to_unix, url_path = win_path_to_unix, url_path

from conda.config import sys_rc_path  # NOQA
sys_rc_path = sys_rc_path

from conda.version import VersionOrder  # NOQA
VersionOrder = VersionOrder


import conda.base.context  # NOQA
import conda.exceptions  # NOQA
from conda.base.context import get_prefix as context_get_prefix, non_x86_linux_machines  # NOQA
non_x86_linux_machines = non_x86_linux_machines

from conda.base.constants import DEFAULT_CHANNELS  # NOQA
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
root_dir = conda.base.context.context.root_dir
root_writable = conda.base.context.context.root_writable
subdir = conda.base.context.context.subdir
from conda.models.channel import get_conda_build_local_url  # NOQA
get_rc_urls = lambda: list(conda.base.context.context.channels)
get_local_urls = lambda: list(get_conda_build_local_url()) or []
load_condarc = lambda fn: conda.base.context.reset_context([fn])
PaddingError = conda.exceptions.PaddingError
