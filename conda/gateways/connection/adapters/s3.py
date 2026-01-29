# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""Defines S3 transport adapter for CondaSession (requests.Session)."""

from __future__ import annotations

from logging import LoggerAdapter, getLogger
from tempfile import SpooledTemporaryFile
from typing import IO, TYPE_CHECKING, Callable

from ....common.compat import ensure_binary
from ....common.serialize import json
from ....common.url import url_to_s3_info
from .. import BaseAdapter, CaseInsensitiveDict, Response

if TYPE_CHECKING:
    from .. import PreparedRequest

log = getLogger(__name__)
stderrlog = LoggerAdapter(getLogger("conda.stderrlog"), extra=dict(terminator="\n"))


class S3Adapter(BaseAdapter):
    def send(
        self,
        request: PreparedRequest,
        stream: bool = False,
        timeout: None | float | tuple[float, float] | tuple[float, None] = None,
        verify: bool | str = True,
        cert: None | bytes | str | tuple[bytes | str, bytes | str] = None,
        proxies: dict[str, str] | None = None,
    ) -> Response:
        resp = Response()
        resp.status_code = 200
        resp.url = request.url

        try:
            return self._send_boto3(resp, request)
        except ImportError:
            stderrlog.info(
                "\nError: boto3 is required for S3 channels. "
                "Please install with `conda install boto3`\n"
                "Make sure to run `conda deactivate` if you "
                "are in a conda environment.\n"
            )
            resp.status_code = 404
            return resp

    def close(self):
        pass

    def download_to_fileobj(
        self,
        url: str,
        fileobj: IO[bytes],
        progress_callback: Callable[[float], None] | None = None,
        size: int | None = None,
    ) -> None:
        """
        Download S3 object directly to file object using boto3's optimized
        download_fileobj, which handles multipart downloads and retries.

        This avoids the extra copy that occurs when using send() which buffers
        to a SpooledTemporaryFile first.

        :param url: S3 URL (s3://bucket/key)
        :param fileobj: File object to write to (must be opened in binary write mode)
        :param progress_callback: Optional callback(fraction) where fraction is 0.0-1.0
        :param size: Optional content length (required for progress reporting)
        :raises ImportError: If boto3 is not installed
        :raises BotoCoreError, ClientError: On S3 errors
        """
        from boto3.session import Session

        bucket_name, key_string = url_to_s3_info(url)
        # Create separate boto3 session for thread safety
        # https://github.com/conda/conda/issues/8993
        session = Session()
        s3 = session.resource("s3")
        key = s3.Object(bucket_name, key_string[1:])

        boto_callback = None
        if progress_callback and size:
            downloaded = [0]

            def boto_callback(bytes_transferred):
                downloaded[0] += bytes_transferred
                progress_callback(downloaded[0] / size)

        key.download_fileobj(fileobj, Callback=boto_callback)

    def _send_boto3(self, resp: Response, request: PreparedRequest) -> Response:
        from boto3.session import Session
        from botocore.exceptions import BotoCoreError, ClientError

        bucket_name, key_string = url_to_s3_info(request.url)
        # https://github.com/conda/conda/issues/8993
        # creating a separate boto3 session to make this thread safe
        session = Session()
        # create a resource client using this thread's session object
        s3 = session.resource("s3")
        # finally get the S3 object
        key = s3.Object(bucket_name, key_string[1:])

        try:
            response = key.get()
        except (BotoCoreError, ClientError) as e:
            resp.status_code = 404
            message = {
                "error": "error downloading file from s3",
                "path": request.url,
                "exception": repr(e),
            }
            resp.raw = self._write_tempfile(
                lambda x: x.write(ensure_binary(json.dumps(message)))
            )
            resp.close = resp.raw.close
            return resp

        key_headers = response["ResponseMetadata"]["HTTPHeaders"]
        resp.headers = CaseInsensitiveDict(
            {
                "Content-Type": key_headers.get("content-type", "text/plain"),
                "Content-Length": key_headers["content-length"],
                "Last-Modified": key_headers["last-modified"],
            }
        )

        resp.raw = self._write_tempfile(key.download_fileobj)
        resp.close = resp.raw.close

        return resp

    def _write_tempfile(self, writer_callable):
        fh = SpooledTemporaryFile()
        writer_callable(fh)
        fh.seek(0)
        return fh
