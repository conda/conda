# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""
Miscellaneous utility functions for sharded repodata processing.

This module contains utility functions that don't fit cleanly into other modules:
- URL handling
- Package name parsing
- Data transformation helpers
- Threading utilities
"""

from __future__ import annotations

import functools
import queue
from contextlib import contextmanager, suppress
from pathlib import Path
from typing import TYPE_CHECKING
from urllib.parse import urljoin, urlparse, urlunparse, uses_relative

from libmambapy.bindings import specs

import conda.gateways.repodata
from _conda.shards.cache import ShardCache
from conda.base.context import context

if TYPE_CHECKING:
    from collections.abc import Iterable, Iterator, Sequence, TypeVar
    from queue import SimpleQueue as Queue

    from _conda.shards_typing import PackageRecordDict, ShardDict

    from _conda.shards.core import Shards

    _T = TypeVar("_T")


# Schemes that urljoin handles correctly (registered in urllib.parse.uses_relative)
_URLJOIN_SAFE_SCHEMES = frozenset(uses_relative)

SHARDS_CONNECTIONS_DEFAULT = 10


def _shards_connections() -> int:
    """
    If context.repodata_threads is not set, find the size of the connection pool
    in a typical https:// session. This should significantly reduce dropped
    connections. We match requests' default 10.

    Is this shared between all sessions? Or do we get a different pool for a
    different get_session(url)?

    Other adapters (file://, s3://) used in conda would have different
    concurrency behavior;  we are not prepared to have separate threadpools per
    connection type.
    """
    if context.repodata_threads is not None:
        return context.repodata_threads
    return SHARDS_CONNECTIONS_DEFAULT


def _safe_urljoin_with_slash(base_url: str, relative_url: str = "") -> str:
    """
    Join base_url with relative_url, ensuring proper handling of all URL schemes.

    Python's urllib.parse.urljoin only handles schemes registered in
    ``urllib.parse.uses_relative``. For unregistered schemes like ``s3://``,
    it returns just ``"."`` instead of the resolved URL. This function falls
    back to a scheme-swap workaround for those cases.

    The result always ends with "/" to enable proper string concatenation with filenames.

    See: https://github.com/conda/conda-libmamba-solver/issues/866
    """
    parsed = urlparse(base_url)

    # For schemes that urljoin handles correctly, use the standard behavior
    if parsed.scheme in _URLJOIN_SAFE_SCHEMES:
        # Standard urljoin behavior: join with relative_url, then "." for trailing slash
        result = urljoin(urljoin(base_url, relative_url), ".")
        return result

    # For unregistered schemes (e.g. s3://), urljoin drops the host.
    # Work around that by temporarily swapping in https://, then restoring
    # the original scheme on the result.
    relative_parsed = urlparse(relative_url)
    if not relative_parsed.scheme and parsed.scheme:
        https_base_url = urlunparse(parsed._replace(scheme="https"))
        joined_https = urljoin(urljoin(https_base_url, relative_url), ".")
        result = urlunparse(urlparse(joined_https)._replace(scheme=parsed.scheme))
    else:
        result = urljoin(urljoin(base_url, relative_url), ".")

    # Ensure trailing slash for proper concatenation
    if not result.endswith("/"):
        result += "/"

    return result


def _is_http_error_most_400_codes(status_code: str | int) -> bool:
    """
    Determine whether the `HTTPError` is an HTTP 400 error code (except for 416).
    """
    return (
        isinstance(status_code, int) and 400 <= status_code < 500 and status_code != 416
    )


def ensure_hex_hash(record: PackageRecordDict):
    """
    Convert bytes checksums to hex; leave unchanged if already str.
    """
    for hash_type in "sha256", "md5":
        if hash_value := record.get(hash_type):
            if not isinstance(hash_value, str):
                record[hash_type] = bytes(hash_value).hex()
    return record


@functools.cache
def spec_to_package_name(spec: str) -> str:
    """
    Given a dependency spec, return the package name.
    """
    # Note: hope for no MatchSpec-without-name in repodata, although it is
    # possible in the MatchSpec grammar.
    parsed_spec = specs.MatchSpec.parse(spec)
    name = str(parsed_spec.name)
    return name


def filter_redundant_packages(repodata: ShardDict, use_only_tar_bz2=False) -> ShardDict:
    """
    Given repodata or a single shard, remove any .tar.bz2 packages that have a
    .conda counterpart.

    Return a shallow copy if use_only_tar_bz2==False, else unmodified input.
    """
    if use_only_tar_bz2:
        return repodata

    _tar_bz2 = ".tar.bz2"
    _conda = ".conda"
    _len_tar_bz2 = len(_tar_bz2)

    legacy_packages = repodata.get("packages", {})
    conda_packages = repodata.get("packages.conda", {})

    return {
        **repodata,
        "packages": {
            k: v
            for k, v in legacy_packages.items()
            if f"{k[:-_len_tar_bz2]}{_conda}" not in conda_packages
        },
    }


def combine_batches_until_none(
    in_queue: Queue[Sequence[_T] | None],
) -> Iterator[Sequence[_T]]:
    """
    Combine lists from in_queue until we see None. Yield combined lists.
    """
    running = True
    while running:
        try:
            # Add timeout to prevent indefinite blocking if producer thread fails
            batch = in_queue.get(timeout=5)
            if batch is None:
                break
        except queue.Empty:
            # If we timeout, continue waiting - producer might still send data
            continue

        node_ids = list(batch)
        with suppress(queue.Empty):
            while True:  # loop exits with break or queue.Empty exception
                batch = in_queue.get_nowait()
                if batch is None:
                    # do the work but then quit
                    running = False
                    break
                else:
                    node_ids.extend(batch)
        yield node_ids


def exception_to_queue(func):
    """
    Decorator to send unhandled exceptions to the second argument out_queue.
    """

    @functools.wraps(func)
    def wrapper(in_queue, out_queue, *args, **kwargs):
        try:
            return func(in_queue, out_queue, *args, **kwargs)
        except BaseException as e:  # includes KeyboardInterrupt
            in_queue.put(None)  # tell worker that we're done
            out_queue.put(e)  # tell caller that we received an exception

    return wrapper


@contextmanager
def _install_shards_cache(shardlikes: Iterable[Shards]):
    """
    Add shards_cache to shardlikes for duration of traversal, then remove and close.
    """
    with ShardCache(Path(conda.gateways.repodata.create_cache_dir())) as cache:
        for shardlike in shardlikes:
            # Only Shards objects (not ShardLike) have this attribute
            if hasattr(shardlike, "shards_cache"):
                shardlike.shards_cache = cache
        yield cache
