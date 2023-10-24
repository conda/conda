# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""Download logic for conda indices and packages."""
from __future__ import annotations

import hashlib
import os
import tempfile
import warnings
from contextlib import contextmanager
from logging import DEBUG, getLogger
from os.path import basename, exists, join
from pathlib import Path

from conda.gateways.disk.lock import lock

from ... import CondaError
from ...auxlib.ish import dals
from ...auxlib.logz import stringify
from ...base.context import context
from ...common.io import time_recorder
from ...exceptions import (
    BasicClobberError,
    ChecksumMismatchError,
    CondaDependencyError,
    CondaHTTPError,
    CondaSSLError,
    ProxyError,
    maybe_raise,
)
from ..disk.delete import rm_rf
from . import (
    ConnectionError,
    HTTPError,
    InsecureRequestWarning,
    InvalidSchema,
    RequestsProxyError,
    SSLError,
)
from .session import get_session

log = getLogger(__name__)


CHUNK_SIZE = 1 << 14


def disable_ssl_verify_warning():
    warnings.simplefilter("ignore", InsecureRequestWarning)


@time_recorder("download")
def download(
    url,
    target_full_path,
    md5=None,
    sha256=None,
    size=None,
    progress_update_callback=None,
):
    if exists(target_full_path):
        maybe_raise(BasicClobberError(target_full_path, url, context), context)
    if not context.ssl_verify:
        disable_ssl_verify_warning()

    with download_http_errors(url):
        download_inner(
            url, target_full_path, md5, sha256, size, progress_update_callback
        )

    with Path(target_full_path).open("rb") as target:
        if md5 or sha256:
            checksum_type = "sha256" if sha256 else "md5"
            checksum = sha256 if sha256 else md5
            hasher = hashlib.new(checksum_type)
            target.seek(0)
            while read := target.read(CHUNK_SIZE):
                hasher.update(read)

            actual_checksum = hasher.hexdigest()

            if actual_checksum != checksum:
                log.debug(
                    "%s mismatch for download: %s (%s != %s)",
                    checksum_type,
                    url,
                    actual_checksum,
                    checksum,
                )
                raise ChecksumMismatchError(
                    url, target_full_path, checksum_type, checksum, actual_checksum
                )
        if size is not None:
            actual_size = os.fstat(target.fileno()).st_size
            if actual_size != size:
                log.debug(
                    "size mismatch for download: %s (%s != %s)", url, actual_size, size
                )
                raise ChecksumMismatchError(
                    url, target_full_path, "size", size, actual_size
                )


def download_inner(url, target_full_path, md5, sha256, size, progress_update_callback):
    timeout = context.remote_connect_timeout_secs, context.remote_read_timeout_secs
    session = get_session(url)

    partial = False
    target_file_for_download = download_full_file
    if size and (md5 or sha256):
        partial = True
        target_file_for_download = download_partial_file

    streamed_bytes = 0
    size_builder = 0

    with target_file_for_download(target_full_path) as target:
        stat_result = os.fstat(target.fileno())
        if size is not None and stat_result.st_size >= size:
            return  # moves partial onto target_path, checksum will be checked

        headers = {}
        if partial and stat_result.st_size > 0:
            headers = {"Range": f"bytes={stat_result.st_size}-"}

        resp = session.get(
            url, stream=True, headers=headers, proxies=session.proxies, timeout=timeout
        )
        if log.isEnabledFor(DEBUG):
            log.debug(stringify(resp, content_max_len=256))
        resp.raise_for_status()

        # Reset file if we think we're downloading partial content but the
        # server doesn't respond with 206 Partial Content
        if partial and resp.status_code != 206:
            target.seek(0)
            target.truncate()

        content_length = int(resp.headers.get("Content-Length", 0))

        for chunk in resp.iter_content(chunk_size=CHUNK_SIZE):
            # chunk could be the decompressed form of the real data
            # but we want the exact number of bytes read till now
            streamed_bytes = resp.raw.tell()
            try:
                target.write(chunk)
            except OSError as e:
                message = "Failed to write to %(target_path)s\n  errno: %(errno)d"
                raise CondaError(message, target_path=target.name, errno=e.errno)
            size_builder += len(chunk)

            if content_length and 0 <= streamed_bytes <= content_length:
                if progress_update_callback:
                    # This is also incorrect during partial downloads. MDN:
                    #
                    # The Content-Length header now indicates the size of the
                    # requested range (and not the full size of the image). The
                    # Content-Range response header indicates where in the full
                    # resource this partial message belongs.
                    progress_update_callback(
                        (stat_result.st_size + streamed_bytes) / content_length
                    )

        if content_length and streamed_bytes != content_length:
            # TODO: needs to be a more-specific error type
            message = dals(
                """
            Downloaded bytes did not match Content-Length
                url: %(url)s
                target_path: %(target_path)s
                Content-Length: %(content_length)d
                downloaded bytes: %(downloaded_bytes)d
            """
            )
            raise CondaError(
                message,
                url=url,
                target_path=target_full_path,
                content_length=content_length,
                downloaded_bytes=streamed_bytes,
            )
    # exit context manager, renaming target to target_full_path


@contextmanager
def download_partial_file(target_full_path: str | Path):
    """
    Create or open locked partial download file, moving onto target_full_path
    when finished. Preserve partial file on exception.
    """
    target_full_path = Path(target_full_path)
    parent = target_full_path.parent
    name = Path(target_full_path).name
    partial_name = f"{name}.partial"
    partial_path = parent / partial_name

    with partial_path.open(mode="a+b") as partial, lock(partial):
        yield partial

    partial_path.rename(target_full_path)


@contextmanager
def download_full_file(target_full_path: str | Path):
    """
    Create or truncate target_full_path.

    Used when partial download is not desired.
    """
    with Path(target_full_path).open("w+b") as target:
        yield target


@contextmanager
def download_http_errors(url: str):
    """Exception translator used inside download()"""
    # This complex exception translation strategy is reminiscent of def
    # conda_http_errors(url, repodata_fn): in gateways/repodata

    try:
        yield

    except ConnectionResetError as e:
        log.debug("%s, trying again" % e)
        # where does retry happen?
        raise

    except RequestsProxyError:
        raise ProxyError()  # see #3962

    except InvalidSchema as e:
        if "SOCKS" in str(e):
            message = dals(
                """
                Requests has identified that your current working environment is configured
                to use a SOCKS proxy, but pysocks is not installed.  To proceed, remove your
                proxy configuration, run `conda install pysocks`, and then you can re-enable
                your proxy configuration.
                """
            )
            raise CondaDependencyError(message)
        else:
            raise

    except SSLError as e:
        # SSLError: either an invalid certificate or OpenSSL is unavailable
        try:
            import ssl  # noqa: F401
        except ImportError:
            raise CondaSSLError(
                dals(
                    f"""
                    OpenSSL appears to be unavailable on this machine. OpenSSL is required to
                    download and install packages.

                    Exception: {e}
                    """
                )
            )
        else:
            raise CondaSSLError(
                dals(
                    f"""
                    Encountered an SSL error. Most likely a certificate verification issue.

                    Exception: {e}
                    """
                )
            )

    except (ConnectionError, HTTPError) as e:
        help_message = dals(
            """
        An HTTP error occurred when trying to retrieve this URL.
        HTTP errors are often intermittent, and a simple retry will get you on your way.
        """
        )
        raise CondaHTTPError(
            help_message,
            url,
            getattr(e.response, "status_code", None),
            getattr(e.response, "reason", None),
            getattr(e.response, "elapsed", None),
            e.response,
            caused_by=e,
        )


def download_text(url):
    if not context.ssl_verify:
        disable_ssl_verify_warning()
    try:
        timeout = context.remote_connect_timeout_secs, context.remote_read_timeout_secs
        session = get_session(url)
        response = session.get(
            url, stream=True, proxies=session.proxies, timeout=timeout
        )
        if log.isEnabledFor(DEBUG):
            log.debug(stringify(response, content_max_len=256))
        response.raise_for_status()
    except RequestsProxyError:
        raise ProxyError()  # see #3962
    except InvalidSchema as e:
        if "SOCKS" in str(e):
            message = dals(
                """
                Requests has identified that your current working environment is configured
                to use a SOCKS proxy, but pysocks is not installed.  To proceed, remove your
                proxy configuration, run `conda install pysocks`, and then you can re-enable
                your proxy configuration.
                """
            )
            raise CondaDependencyError(message)
        else:
            raise
    except (ConnectionError, HTTPError, SSLError) as e:
        status_code = getattr(e.response, "status_code", None)
        if status_code == 404:
            help_message = dals(
                """
            An HTTP error occurred when trying to retrieve this URL.
            The URL does not exist.
            """
            )
        else:
            help_message = dals(
                """
            An HTTP error occurred when trying to retrieve this URL.
            HTTP errors are often intermittent, and a simple retry will get you on your way.
            """
            )
        raise CondaHTTPError(
            help_message,
            url,
            status_code,
            getattr(e.response, "reason", None),
            getattr(e.response, "elapsed", None),
            e.response,
            caused_by=e,
        )
    return response.text


class TmpDownload:
    """Context manager to handle downloads to a tempfile."""

    def __init__(self, url, verbose=True):
        self.url = url
        self.verbose = verbose

    def __enter__(self):
        if "://" not in self.url:
            # if we provide the file itself, no tmp dir is created
            self.tmp_dir = None
            return self.url
        else:
            self.tmp_dir = tempfile.mkdtemp()
            dst = join(self.tmp_dir, basename(self.url))
            download(self.url, dst)
            return dst

    def __exit__(self, exc_type, exc_value, traceback):
        if self.tmp_dir:
            rm_rf(self.tmp_dir)
