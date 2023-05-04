# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
import errno
import functools
import os
import sys
import threading
from builtins import input  # noqa: F401
from collections.abc import Hashable as _Hashable

# necessary for conda-build
from io import StringIO  # noqa: F401

from . import CondaError  # noqa: F401
from .base.context import reset_context
from .deprecations import deprecated

reset_context()  # initialize context when conda.exports is imported

from . import plan  # noqa: F401
from .cli.common import spec_from_line, specs_from_args, specs_from_url  # noqa: F401
from .cli.conda_argparse import ArgumentParser  # noqa: F401
from .cli.conda_argparse import add_parser_channels, add_parser_prefix  # noqa: F401
from .common import compat  # noqa: F401
from .common.compat import on_win  # noqa: F401
from .common.toposort import _toposort  # noqa: F401
from .core.solve import Solver  # noqa: F401
from .gateways.connection.download import TmpDownload  # noqa: F401
from .gateways.connection.download import download as _download  # noqa: F401
from .gateways.connection.session import CondaSession  # noqa: F401
from .gateways.disk.create import TemporaryDirectory  # noqa: F401
from .gateways.disk.link import lchmod  # noqa: F401


@deprecated("23.3", "23.9", addendum="Handled by CondaSession.")
def handle_proxy_407(x, y):
    pass


from .core.package_cache_data import rm_fetched  # noqa: F401
from .gateways.disk.delete import delete_trash, move_to_trash  # noqa: F401
from .misc import untracked, walk_prefix  # noqa: F401
from .resolve import (  # noqa: F401
    MatchSpec,
    Resolve,
    ResolvePackageNotFound,
    Unsatisfiable,
)

NoPackagesFound = NoPackagesFoundError = ResolvePackageNotFound

import conda.base.context

from .base.context import (  # noqa: F401
    get_prefix,
    non_x86_machines,
    reset_context,
    sys_rc_path,
)
from .common.path import win_path_to_unix  # noqa: F401
from .gateways.disk.read import compute_md5sum  # noqa: F401
from .models.channel import Channel  # noqa: F401
from .models.version import VersionOrder, normalized_version  # noqa: F401
from .utils import (  # noqa: F401
    hashsum_file,
    human_bytes,
    md5_file,
    unix_path_to_win,
    url_path,
)

non_x86_linux_machines = non_x86_machines

from .auxlib.entity import EntityEncoder  # noqa: F401
from .base.constants import (  # noqa: F401
    DEFAULT_CHANNELS,
    DEFAULT_CHANNELS_UNIX,
    DEFAULT_CHANNELS_WIN,
)

get_default_urls = lambda: DEFAULT_CHANNELS

from .base.constants import PREFIX_PLACEHOLDER

_PREFIX_PLACEHOLDER = prefix_placeholder = PREFIX_PLACEHOLDER

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
conda_build = conda.base.context.context.conda_build

from .models.channel import get_conda_build_local_url  # NOQA

get_rc_urls = lambda: list(conda.base.context.context.channels)
get_local_urls = lambda: list(get_conda_build_local_url()) or []
load_condarc = lambda fn: conda.base.context.reset_context([fn])

from .exceptions import CondaOSError, LinkError, PaddingError, PathNotFoundError  # NOQA

PaddingError = PaddingError
LinkError = LinkError
CondaOSError = CondaOSError
# PathNotFoundError is the conda 4.4.x name for it - let's plan ahead.
PathNotFoundError = CondaFileNotFoundError = PathNotFoundError

from .models.enums import FileMode  # noqa: F401
from .models.enums import PathType  # noqa: F401
from .models.records import PackageRecord

IndexRecord = PackageRecord

from .core.package_cache_data import ProgressiveFetchExtract  # noqa: F401
from .core.subdir_data import cache_fn_url  # noqa: F401
from .exceptions import CondaHTTPError, LockError, UnsatisfiableError  # noqa: F401
from .gateways.subprocess import ACTIVE_SUBPROCESSES, subprocess_call  # noqa: F401
from .models.dist import Dist

# Replacements for six exports for compatibility
PY3 = True  # noqa: F401
string_types = str  # noqa: F401
text_type = str  # noqa: F401


def iteritems(d, **kw):
    return iter(d.items(**kw))


class Completer:  # pragma: no cover
    def get_items(self):
        return self._get_items()

    def __contains__(self, item):
        return True

    def __iter__(self):
        return iter(self.get_items())


class InstalledPackages:
    pass


@deprecated("23.3", "23.9", addendum="Use `functools.lru_cache` instead.")
class memoized:  # pragma: no cover
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
            elif not isinstance(arg, _Hashable):
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


from .core.prefix_data import delete_prefix_from_linked_data
from .gateways.disk.delete import rm_rf as _rm_rf


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


from .plan import display_actions as _display_actions
from .plan import (  # noqa: F401
    execute_actions,
    execute_instructions,
    execute_plan,
    install_actions,
)


def display_actions(
    actions, index, show_channel_urls=None, specs_to_remove=(), specs_to_add=()
):
    if "FETCH" in actions:
        actions["FETCH"] = [index[d] for d in actions["FETCH"]]
    if "LINK" in actions:
        actions["LINK"] = [index[d] for d in actions["LINK"]]
    if "UNLINK" in actions:
        actions["UNLINK"] = [index[d] for d in actions["UNLINK"]]
    index = {prec: prec for prec in index.values()}
    return _display_actions(
        actions, index, show_channel_urls, specs_to_remove, specs_to_add
    )


from .core.index import dist_str_in_index  # noqa: F401
from .core.index import fetch_index as _fetch_index  # noqa: F401
from .core.index import get_index as _get_index


def get_index(
    channel_urls=(),
    prepend=True,
    platform=None,
    use_local=False,
    use_cache=False,
    unknown=None,
    prefix=None,
):
    index = _get_index(
        channel_urls, prepend, platform, use_local, use_cache, unknown, prefix
    )
    return {Dist(prec): prec for prec in index.values()}


def fetch_index(channel_urls, use_cache=False, index=None):
    index = _fetch_index(channel_urls, use_cache, index)
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


def symlink_conda(prefix, root_dir, shell=None):  # pragma: no cover
    print("WARNING: symlink_conda() is deprecated.", file=sys.stderr)
    # do not symlink root env - this clobbers activate incorrectly.
    # prefix should always be longer than, or outside the root dir.
    if os.path.normcase(os.path.normpath(prefix)) in os.path.normcase(
        os.path.normpath(root_dir)
    ):
        return
    if on_win:
        where = "condabin"
        symlink_fn = functools.partial(win_conda_bat_redirect, shell=shell)
    else:
        where = "bin"
        symlink_fn = os.symlink
    if not os.path.isdir(os.path.join(prefix, where)):
        os.makedirs(os.path.join(prefix, where))
    _symlink_conda_hlp(prefix, root_dir, where, symlink_fn)


def _symlink_conda_hlp(prefix, root_dir, where, symlink_fn):  # pragma: no cover
    scripts = ["conda", "activate", "deactivate"]
    prefix_where = os.path.join(prefix, where)
    if not os.path.isdir(prefix_where):
        os.makedirs(prefix_where)
    for f in scripts:
        root_file = os.path.join(root_dir, where, f)
        prefix_file = os.path.join(prefix_where, f)
        try:
            # try to kill stale links if they exist
            if os.path.lexists(prefix_file):
                rm_rf(prefix_file)
            # if they're in use, they won't be killed.  Skip making new symlink.
            if not os.path.lexists(prefix_file):
                symlink_fn(root_file, prefix_file)
        except OSError as e:
            if os.path.lexists(prefix_file) and (
                e.errno in (errno.EPERM, errno.EACCES, errno.EROFS, errno.EEXIST)
            ):
                # Cannot symlink root_file to prefix_file. Ignoring since link already exists
                pass
            else:
                raise


if on_win:  # pragma: no cover

    def win_conda_bat_redirect(src, dst, shell):
        """Special function for Windows XP where the `CreateSymbolicLink`
        function is not available.

        Simply creates a `.bat` file at `dst` which calls `src` together with
        all command line arguments.

        Works of course only with callable files, e.g. `.bat` or `.exe` files.
        """
        from .utils import shells

        try:
            os.makedirs(os.path.dirname(dst))
        except OSError as exc:  # Python >2.5
            if exc.errno == errno.EEXIST and os.path.isdir(os.path.dirname(dst)):
                pass
            else:
                raise

        # bat file redirect
        if not os.path.isfile(dst + ".bat"):
            with open(dst + ".bat", "w") as f:
                f.write('@echo off\ncall "%s" %%*\n' % src)

        # TODO: probably need one here for powershell at some point

        # This one is for bash/cygwin/msys
        # set default shell to bash.exe when not provided, as that's most common
        if not shell:
            shell = "bash.exe"

        # technically these are "links" - but islink doesn't work on win
        if not os.path.isfile(dst):
            with open(dst, "w") as f:
                f.write("#!/usr/bin/env bash \n")
                if src.endswith("conda"):
                    f.write('%s "$@"' % shells[shell]["path_to"](src + ".exe"))
                else:
                    f.write('source %s "$@"' % shells[shell]["path_to"](src))
            # Make the new file executable
            # http://stackoverflow.com/a/30463972/1170370
            mode = os.stat(dst).st_mode
            mode |= (mode & 292) >> 2  # copy R bits to X
            os.chmod(dst, mode)


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
