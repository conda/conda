# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""Backported exports for conda-build."""

from __future__ import annotations

from builtins import input  # noqa: UP029
from io import StringIO
from typing import TYPE_CHECKING

from . import CondaError
from .base.constants import (
    DEFAULT_CHANNELS,
    DEFAULT_CHANNELS_UNIX,
    DEFAULT_CHANNELS_WIN,
    PREFIX_PLACEHOLDER,
)
from .base.context import (
    context,
    non_x86_machines,
    reset_context,
    sys_rc_path,
)
from .cli.common import spec_from_line, specs_from_args, specs_from_url
from .cli.conda_argparse import ArgumentParser
from .cli.helpers import (
    add_parser_channels,
    add_parser_prefix,
)
from .common import compat
from .common.serialize.json import CondaJSONEncoder
from .common.toposort import _toposort
from .core.index import (
    Index,
    dist_str_in_index,
)
from .core.package_cache_data import ProgressiveFetchExtract
from .core.prefix_data import delete_prefix_from_linked_data
from .core.solve import Solver
from .core.subdir_data import cache_fn_url
from .deprecations import deprecated
from .exceptions import (
    CondaHTTPError,
    CondaOSError,
    LinkError,
    LockError,
    PaddingError,
    PathNotFoundError,
    UnsatisfiableError,
)
from .gateways.connection.download import TmpDownload
from .gateways.connection.download import download as _download
from .gateways.connection.session import CondaSession
from .gateways.disk.create import TemporaryDirectory
from .gateways.disk.delete import delete_trash
from .gateways.disk.link import lchmod
from .gateways.subprocess import ACTIVE_SUBPROCESSES, subprocess_call
from .misc import untracked, walk_prefix
from .models.channel import Channel, get_conda_build_local_url
from .models.dist import Dist
from .models.enums import FileMode, PathEnum
from .models.version import VersionOrder, normalized_version
from .resolve import (
    MatchSpec,
    Resolve,
    ResolvePackageNotFound,
    Unsatisfiable,
)
from .utils import human_bytes, url_path

if TYPE_CHECKING:
    from typing import Any

__all__ = [
    "_toposort",
    "ACTIVE_SUBPROCESSES",
    "add_parser_channels",
    "add_parser_prefix",
    "annotations",
    "arch_name",
    "ArgumentParser",
    "binstar_upload",
    "bits",
    "cache_fn_url",
    "Channel",
    "compat",
    "conda_build",
    "CondaError",
    "CondaHTTPError",
    "CondaJSONEncoder",
    "CondaOSError",
    "CondaSession",
    "context",
    "DEFAULT_CHANNELS_UNIX",
    "DEFAULT_CHANNELS_WIN",
    "DEFAULT_CHANNELS",
    "default_prefix",
    "default_python",
    "delete_prefix_from_linked_data",
    "delete_trash",
    "deprecated",
    "dist_str_in_index",
    "Dist",
    "download",
    "envs_dirs",
    "FileMode",
    "get_conda_build_local_url",
    "get_default_urls",
    "get_index",
    "get_local_urls",
    "get_rc_urls",
    "human_bytes",
    "Index",
    "input",
    "is_linked",
    "lchmod",
    "linked_data",
    "linked",
    "LinkError",
    "load_condarc",
    "LockError",
    "MatchSpec",
    "non_x86_linux_machines",
    "non_x86_machines",
    "NoPackagesFound",
    "NoPackagesFoundError",
    "normalized_version",
    "package_cache",
    "PaddingError",
    "PathEnum",
    "PathNotFoundError",
    "pkgs_dirs",
    "platform",
    "PREFIX_PLACEHOLDER",
    "ProgressiveFetchExtract",
    "reset_context",
    "Resolve",
    "ResolvePackageNotFound",
    "rm_rf",
    "root_dir",
    "root_writable",
    "Solver",
    "spec_from_line",
    "specs_from_args",
    "specs_from_url",
    "StringIO",
    "subdir",
    "subprocess_call",
    "sys_rc_path",
    "TemporaryDirectory",
    "TmpDownload",
    "TYPE_CHECKING",
    "Unsatisfiable",
    "UnsatisfiableError",
    "untracked",
    "url_path",
    "VersionOrder",
    "walk_prefix",
]

reset_context()  # initialize context when conda.exports is imported


NoPackagesFound = NoPackagesFoundError = ResolvePackageNotFound
non_x86_linux_machines = non_x86_machines
arch_name = context.arch_name
binstar_upload = context.anaconda_upload
bits = context.bits
default_prefix = context.default_prefix
default_python = context.default_python
envs_dirs = context.envs_dirs
pkgs_dirs = context.pkgs_dirs
platform = context.platform
root_dir = context.root_prefix
root_writable = context.root_writable
subdir = context.subdir
conda_build = context.conda_build
get_rc_urls = lambda: list(context.channels)
get_local_urls = lambda: list(get_conda_build_local_url()) or []
load_condarc = lambda fn: reset_context([fn])
PaddingError = PaddingError
LinkError = LinkError
CondaOSError = CondaOSError
# Replacements for six exports for compatibility


# FUTURE: conda 26.3+ remove this
def __getattr__(name: str) -> Any:
    # lazy load the deprecated module
    if name == "plan":
        from . import plan

        return plan

    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")


def get_default_urls():
    from .base.constants import DEFAULT_CHANNELS

    return DEFAULT_CHANNELS


def rm_rf(path, max_retries=5, trash=True):
    from .gateways.disk.delete import rm_rf

    rm_rf(path)
    delete_prefix_from_linked_data(path)


def get_index(
    channel_urls=(),
    prepend=True,
    platform=None,
    use_local=False,
    use_cache=False,
    unknown=None,
    prefix=None,
):
    # XXX this function is passing use_local in subdirs=' place; it makes no sense.
    index = Index(
        channel_urls, prepend, platform, use_local, use_cache, unknown, prefix
    )
    return {Dist(prec): prec for prec in index.values()}


def package_cache():
    from .core.package_cache_data import PackageCacheData

    class package_cache:
        def __contains__(self, dist):
            return bool(
                PackageCacheData.first_writable().get(Dist(dist).to_package_ref(), None)
            )

        def keys(self):
            return (Dist(v) for v in PackageCacheData.first_writable().values())

        def __delitem__(self, dist):
            PackageCacheData.first_writable().remove(Dist(dist).to_package_ref())

    return package_cache()


def linked_data(prefix, ignore_channels=False):
    """Return a dictionary of the linked packages in prefix."""
    from .core.prefix_data import PrefixData
    from .models.dist import Dist

    pd = PrefixData(prefix)
    return {
        Dist(prefix_record): prefix_record
        for prefix_record in pd._prefix_records.values()
    }


def linked(prefix, ignore_channels=False):
    """Return the Dists of linked packages in prefix."""
    from .models.enums import PackageType

    conda_package_types = PackageType.conda_package_types()
    ld = linked_data(prefix, ignore_channels=ignore_channels).items()
    return {
        dist
        for dist, prefix_rec in ld
        if prefix_rec.package_type in conda_package_types
    }


# exports
def is_linked(prefix, dist):
    """
    Return the install metadata for a linked package in a prefix, or None
    if the package is not linked in the prefix.
    """
    # FIXME Functions that begin with `is_` should return True/False
    from .core.prefix_data import PrefixData

    pd = PrefixData(prefix)
    prefix_record = pd.get(dist.name, None)
    if prefix_record is None:
        return None
    elif MatchSpec(dist).match(prefix_record):
        return prefix_record
    else:
        return None


def download(
    url,
    dst_path,
    session=None,
    md5sum=None,
    urlstxt=False,
    retries=3,
    sha256=None,
    size=None,
):
    return _download(url, dst_path, md5=md5sum, sha256=sha256, size=size)
