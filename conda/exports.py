# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""Backported exports for conda-build."""

from __future__ import annotations

from builtins import input  # noqa: F401, UP029
from io import StringIO  # noqa: F401, for conda-build
from typing import TYPE_CHECKING

from . import CondaError  # noqa: F401
from .base.constants import (  # noqa: F401
    DEFAULT_CHANNELS,
    DEFAULT_CHANNELS_UNIX,
    DEFAULT_CHANNELS_WIN,
    PREFIX_PLACEHOLDER,
)
from .base.context import (  # noqa: F401
    context,
    non_x86_machines,
    reset_context,
    sys_rc_path,
)
from .cli.common import spec_from_line, specs_from_args, specs_from_url  # noqa: F401
from .cli.conda_argparse import ArgumentParser  # noqa: F401
from .cli.helpers import (  # noqa: F401
    add_parser_channels,
    add_parser_prefix,
)
from .common import compat  # noqa: F401
from .common.serialize.json import CondaJSONEncoder
from .common.toposort import _toposort  # noqa: F401
from .core.index import (
    Index,
    dist_str_in_index,  # noqa: F401
)
from .core.package_cache_data import ProgressiveFetchExtract  # noqa: F401
from .core.prefix_data import delete_prefix_from_linked_data
from .core.solve import Solver  # noqa: F401
from .core.subdir_data import cache_fn_url  # noqa: F401
from .deprecations import deprecated
from .exceptions import (  # noqa: F401
    CondaHTTPError,
    CondaOSError,
    LinkError,
    LockError,
    PaddingError,
    PathNotFoundError,
    UnsatisfiableError,
)
from .gateways.connection.download import TmpDownload  # noqa: F401
from .gateways.connection.download import download as _download
from .gateways.connection.session import CondaSession  # noqa: F401
from .gateways.disk.create import TemporaryDirectory  # noqa: F401
from .gateways.disk.delete import delete_trash  # noqa: F401
from .gateways.disk.link import lchmod  # noqa: F401
from .gateways.subprocess import ACTIVE_SUBPROCESSES, subprocess_call  # noqa: F401
from .misc import untracked, walk_prefix  # noqa: F401
from .models.channel import Channel, get_conda_build_local_url  # noqa: F401
from .models.dist import Dist
from .models.enums import FileMode, PathType  # noqa: F401
from .models.version import VersionOrder, normalized_version  # noqa: F401
from .resolve import (  # noqa: F401
    MatchSpec,
    Resolve,
    ResolvePackageNotFound,
    Unsatisfiable,
)
from .utils import human_bytes, url_path  # noqa: F401

if TYPE_CHECKING:
    from typing import Any

reset_context()  # initialize context when conda.exports is imported


NoPackagesFound = NoPackagesFoundError = ResolvePackageNotFound
non_x86_linux_machines = non_x86_machines
get_default_urls = lambda: DEFAULT_CHANNELS
_PREFIX_PLACEHOLDER = prefix_placeholder = PREFIX_PLACEHOLDER
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
# PathNotFoundError is the conda 4.4.x name for it - let's plan ahead.
CondaFileNotFoundError = PathNotFoundError
# Replacements for six exports for compatibility
PY3 = True
string_types = str
text_type = str


# FUTURE: conda 26.3+ remove this
def __getattr__(name: str) -> Any:
    # lazy load the deprecated module
    if name == "plan":
        from . import plan

        return plan

    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")


deprecated.constant(
    "26.3",
    "26.9",
    "EntityEncoder",
    CondaJSONEncoder,
    addendum="Use `conda.common.serialize.json.CondaJSONEncoder` instead.",
)
del CondaJSONEncoder


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
