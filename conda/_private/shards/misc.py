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
import logging
import queue
from contextlib import suppress
from typing import TYPE_CHECKING
from urllib.parse import urljoin, urlparse, urlunparse, uses_relative

from conda.base.context import context
from conda.exceptions import InvalidMatchSpec
from conda.models.match_spec import MatchSpec

if TYPE_CHECKING:
    from collections.abc import Iterator, Sequence
    from queue import SimpleQueue as Queue
    from typing import TypeVar

    from conda._private.shards.typing import PackageRecordDict, ShardDict

    _T = TypeVar("_T")


log = logging.getLogger(__name__)

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
    relative_parsed = urlparse(relative_url)

    # For schemes that urljoin handles correctly, use the standard behavior
    if parsed.scheme in _URLJOIN_SAFE_SCHEMES:
        # Standard urljoin behavior: join with relative_url
        # If relative_url is absolute (has a scheme), it will override base_url entirely
        # Otherwise, treat last segment as filename and strip it with "."
        if relative_parsed.scheme:
            # Absolute URL: use as-is (the trailing slash will be added at the end)
            result = relative_url
        else:
            # Relative URL: join and normalize to directory by appending "."
            result = urljoin(urljoin(base_url, relative_url), ".")
    else:
        # For unregistered schemes (e.g. s3://), urljoin drops the host.
        # Work around that by temporarily swapping in https://, then restoring
        # the original scheme on the result.
        if relative_parsed.scheme:
            # Absolute URL with same scheme: override base_url
            result = relative_url
        elif not relative_parsed.scheme and parsed.scheme:
            # Relative URL: use scheme-swap workaround
            https_base_url = urlunparse(parsed._replace(scheme="https"))
            joined_https = urljoin(urljoin(https_base_url, relative_url), ".")
            result = urlunparse(urlparse(joined_https)._replace(scheme=parsed.scheme))
        else:
            # Fallback for edge cases
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
def spec_to_package_name(spec: str) -> str | None:
    """
    Given a dependency spec, return the package name, or None if the spec is
    not parseable.

    Uses conda's MatchSpec rather than libmambapy to avoid a hard dependency
    on a solver backend. With @functools.cache the performance is equivalent
    (benchmarked at ~10ms for 5000 unique specs either way).
    """
    try:
        return MatchSpec(spec).name
    except InvalidMatchSpec:
        log.warning("Could not parse dependency spec %r; skipping", spec)
        return None


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
