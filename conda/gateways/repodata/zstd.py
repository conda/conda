# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""Zstd interface for repodata."""

from __future__ import annotations

import io
import logging
import os
import re
import time
from contextlib import contextmanager
from hashlib import blake2b
from typing import TYPE_CHECKING

import zstandard
from requests import HTTPError

from ...base.constants import REPODATA_FN
from ...base.context import context
from ...common.serialize import json
from ...common.url import mask_anaconda_token
from ..connection.download import disable_ssl_verify_warning
from ..connection.session import get_session
from . import (
    URL_KEY,
    RepodataOnDisk,
    RepodataState,
    RepoInterface,
    Response304ContentUnchanged,
    conda_http_errors,
)

if TYPE_CHECKING:
    import pathlib

    from ..connection import Session
    from . import RepodataCache

log = logging.getLogger(__name__)

DIGEST_SIZE = 32
NOMINAL_HASH = "blake2_256_nominal"
ON_DISK_HASH = "blake2_256"


def hash():
    """Create a blake2b hasher."""
    return blake2b(digest_size=DIGEST_SIZE)


def withext(url, ext):
    """Change file extension in URL."""
    return re.sub(r"(\.\w+)$", ext, url)


@contextmanager
def timeme(message):
    """Context manager for timing operations."""
    begin = time.monotonic()
    yield
    end = time.monotonic()
    log.debug("%sTook %0.02fs", message, end - begin)


def build_headers(json_path: pathlib.Path, state: RepodataState):
    """Build caching headers for a path and state."""
    headers = {}
    if json_path.exists():
        etag = state.get("_etag")
        if etag:
            headers["if-none-match"] = etag
    return headers


class HashWriter(io.RawIOBase):
    """File writer that hashes data while writing."""

    def __init__(self, backing, hasher):
        self.backing = backing
        self.hasher = hasher

    def write(self, b: bytes):
        self.hasher.update(b)
        return self.backing.write(b)

    def close(self):
        self.backing.close()


def download_and_hash(
    hasher,
    url,
    json_path: pathlib.Path,
    session: Session,
    state: RepodataState | None,
    is_zst=False,
    dest_path: pathlib.Path | None = None,
):
    """Download url, passing bytes through hasher.update().

    json_path: Path of old cached data (ignore etag if not exists).
    dest_path: Path to write new data.
    """
    if dest_path is None:
        dest_path = json_path
    state = state or RepodataState()
    headers = build_headers(json_path, state)
    timeout = context.remote_connect_timeout_secs, context.remote_read_timeout_secs
    response = session.get(url, stream=True, timeout=timeout, headers=headers)
    log.debug("%s %s", url, response.headers)
    response.raise_for_status()
    length = 0
    if response.status_code == 200:
        if is_zst:
            decompressor = zstandard.ZstdDecompressor()
            writer = decompressor.stream_writer(
                HashWriter(dest_path.open("wb"), hasher),  # type: ignore
                closefd=True,
            )
        else:
            writer = HashWriter(dest_path.open("wb"), hasher)
        with writer as repodata:
            for block in response.iter_content(chunk_size=1 << 14):
                repodata.write(block)
    if response.request:
        try:
            length = int(response.headers["Content-Length"])
        except (KeyError, ValueError, AttributeError):
            pass
        log.info("Download %d bytes %r", length, response.request.headers)
    return response


def _is_http_error_most_400_codes(e: HTTPError) -> bool:
    """Determine if HTTP error is a 4xx error (except 416)."""
    if e.response is None:
        return False
    status_code = e.response.status_code
    return 400 <= status_code < 500 and status_code != 416


class ZstSkip(Exception):
    """Exception to skip zst format check."""

    pass


def request_url_zstd_state(
    url,
    state: RepodataState,
    *,
    session: Session,
    cache: RepodataCache,
    temp_path: pathlib.Path,
) -> dict | None:
    """
    Download .json.zst file and return parsed JSON.

    Args:
        url: URL to download from
        state: Repodata state
        session: Session object
        cache: Repodata cache
        temp_path: Temporary path to write json to
    Returns:
        dict | None: Parsed JSON or None if error
    """
    json_path = cache.cache_path_json

    hasher = hash()
    with timeme(f"Download complete {url} "):
        # Just try downloading .json.zst
        try:
            response = download_and_hash(
                hasher,
                withext(url, ".json.zst"),
                json_path,  # makes conditional request if exists
                dest_path=temp_path,  # writes to
                session=session,
                state=state,
                is_zst=True,
            )
        except (HTTPError, zstandard.ZstdError) as e:
            if isinstance(e, zstandard.ZstdError):
                log.warning(
                    "Could not decompress %s as zstd. Fall back to .json. (%s)",
                    mask_anaconda_token(withext(url, ".json.zst")),
                    e,
                )
            if isinstance(e, HTTPError) and not _is_http_error_most_400_codes(e):
                raise

            # zst format is not available, so fallback to .json
            state.set_has_format("zst", False)
            response = download_and_hash(
                hasher,
                withext(url, ".json"),
                json_path,
                dest_path=temp_path,
                session=session,
                state=state,
            )

        # will we use state['headers'] for caching against
        state["_mod"] = response.headers.get("last-modified")
        state["_etag"] = response.headers.get("etag")
        state["_cache_control"] = response.headers.get("cache-control")

    # Handle 304 Not Modified
    if response.status_code == 304:
        raise Response304ContentUnchanged()

    # If we downloaded new data (200), parse and return it
    if response.status_code == 200:
        state[NOMINAL_HASH] = state[ON_DISK_HASH] = hasher.hexdigest()

        # Parse the downloaded JSON
        with temp_path.open("rb") as f:
            repodata_json = json.loads(f.read().decode("utf-8"))

        return repodata_json

    # If something else happened (shouldn't happen, but defensive)
    return None


class ZstdRepoInterface(RepoInterface):
    def __init__(
        self,
        url: str,
        repodata_fn: str | None,
        *,
        cache: RepodataCache,
        **kwargs,
    ) -> None:
        log.debug("Using %s", self.__class__.__name__)

        self._cache = cache

        self._url = url
        self._repodata_fn = repodata_fn or REPODATA_FN

        self._log = logging.getLogger(__name__)
        self._stderrlog = logging.getLogger("conda.stderrlog")

    def repodata(self, state: dict | RepodataState) -> str | None:
        """
        Fetch newest repodata if necessary.

        Always writes to ``cache_path_json``.
        """
        self.repodata_parsed(state)
        raise RepodataOnDisk()

    def repodata_parsed(self, state: dict | RepodataState) -> dict | None:
        """
        Use this to avoid a redundant parse when repodata is updated.

        When repodata is not updated, it doesn't matter whether this function or
        the caller reads from a file.
        """
        session = get_session(self._url)

        if not context.ssl_verify:
            disable_ssl_verify_warning()

        repodata_url = f"{self._url}/{self._repodata_fn}"

        # XXX won't modify caller's state dict
        state_ = self._repodata_state_copy(state)

        # at this point, self._cache.state == state == state_

        temp_path = (
            self._cache.cache_dir / f"{self._cache.name}.{os.urandom(2).hex()}.tmp"
        )
        try:
            with conda_http_errors(self._url, self._repodata_fn):
                repodata_json_or_none = request_url_zstd_state(
                    repodata_url,
                    state_,
                    session=session,
                    cache=self._cache,
                    temp_path=temp_path,
                )

                # update caller's state dict-or-RepodataState. Do this before
                # the self._cache.replace() call which also writes state, then
                # signal not to write state to caller.
                state.update(state_)

                state[URL_KEY] = self._url

                self._cache.state.update(state)

            if temp_path.exists():
                self._cache.replace(temp_path)
        except Response304ContentUnchanged:
            raise
        finally:
            # Clean up the temporary file. In the successful case it raises
            # OSError as self._cache_replace() removed temp_file.
            try:
                temp_path.unlink()
            except OSError:
                pass

        if repodata_json_or_none is None:  # common
            # Indicate that subdir_data mustn't rewrite cache_path_json
            raise RepodataOnDisk()
        else:
            return repodata_json_or_none

    def _repodata_state_copy(self, state: dict | RepodataState) -> RepodataState:
        """Create a copy of state to avoid modifying the caller's dict."""
        if isinstance(state, RepodataState):
            return RepodataState(dict(state))
        else:
            return RepodataState(state)
