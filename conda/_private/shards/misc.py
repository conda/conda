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
from conda.models.records import AttestationsSha256Field

if TYPE_CHECKING:
    from collections.abc import Iterable, Iterator, Sequence
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


# Rattler shards encode hashes as raw bytes. Older shards can use integer arrays
# for package hashes.
HASH_FIELDS = ("sha256", "md5", "legacy_bz2_md5", "attestations_sha256")


def _ensure_hex_hash(record: PackageRecordDict):
    """Normalize shard hashes and validate the attestation digest."""
    for hash_type in HASH_FIELDS:
        if hash_type not in record:
            continue
        hash_value = record[hash_type]
        if hash_type == "attestations_sha256":
            if isinstance(hash_value, bytes) and len(hash_value) == 32:
                hash_value = hash_value.hex()
            record[hash_type] = AttestationsSha256Field.validate_digest(hash_value)
        elif hash_value and not isinstance(hash_value, str):
            record[hash_type] = bytes(hash_value).hex()
    return record


def _iter_shard_records(
    shard: ShardDict, repodata_version: int = 1
) -> Iterable[PackageRecordDict]:
    """
    Yield every package record in a shard: classic ``packages``,
    ``packages.conda``, and (when ``repodata_version >= 3``) all ``v3`` groups.
    """
    for record in shard.get("packages", {}).values():
        yield record
    for record in shard.get("packages.conda", {}).values():
        yield record
    if repodata_version >= 3 and (v3_data := shard.get("v3")):
        for group in v3_data.values():
            for record in group.values():
                yield record


def ensure_hex_hashes(shard: ShardDict) -> ShardDict:
    """
    Convert the raw-bytes hash digests of every record in ``shard`` to hex, in
    place, when the shard is decoded for use.

    Shards are msgpack, where rattler (e.g. ``rattler-index``) encodes hash
    digests as bytes or arrays of ints; ``repodata.json`` and downstream
    consumers expect hex strings. Calling this once as a shard is decoded keeps
    every reader (``iter_records_v3``, ``build_repodata``, ...) free of raw
    bytes, and avoids re-normalizing the same records on each read. The shard
    cache stores the original compressed bytes unchanged; only the decoded
    in-memory dict is modified.
    """
    # repodata_version=3 so v3 records, when present, are always included.
    for record in _iter_shard_records(shard, repodata_version=3):
        _ensure_hex_hash(record)
    return shard


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

    Also filters redundant stems under ``v3["tar.bz2"]`` when a matching stem
    exists in ``v3["conda"]``, ``packages.conda``, or classic ``packages``.

    Return a shallow copy if use_only_tar_bz2==False, else unmodified input.
    """
    if use_only_tar_bz2:
        return repodata

    _tar_bz2 = ".tar.bz2"
    _conda = ".conda"
    _len_tar_bz2 = len(_tar_bz2)
    _len_conda = len(_conda)

    legacy_packages = repodata.get("packages", {})
    conda_packages = repodata.get("packages.conda", {})

    # Stem sets so the hot loops avoid per-key lookups.
    conda_stems = {k[:-_len_conda] for k in conda_packages}
    legacy_stems = {k[:-_len_tar_bz2] for k in legacy_packages}

    result: ShardDict = {
        **repodata,
        "packages": {
            k: v
            for k, v in legacy_packages.items()
            if k[:-_len_tar_bz2] not in conda_stems
        },
    }

    if v3 := repodata.get("v3"):
        v3_conda = v3.get("conda", {})
        all_stems = conda_stems | legacy_stems | set(v3_conda)
        result["v3"] = {
            **v3,
            "tar.bz2": {
                k: v for k, v in v3.get("tar.bz2", {}).items() if (k not in all_stems)
            },
        }

    return result


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
