# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function, unicode_literals

import json
from logging import LoggerAdapter, getLogger
from tempfile import SpooledTemporaryFile

from .. import BaseAdapter, CaseInsensitiveDict, Response
from ....common.compat import ensure_binary
from ....common.url import url_to_s3_info

log = getLogger(__name__)
stderrlog = LoggerAdapter(getLogger('conda.stderrlog'), extra=dict(terminator="\n"))


class S3Adapter(BaseAdapter):

    def __init__(self):
        super(S3Adapter, self).__init__()

    def send(self, request, stream=None, timeout=None, verify=None, cert=None, proxies=None):
        resp = Response()
        resp.status_code = 200
        resp.url = request.url

        try:
            import boto3
            return self._send_boto3(boto3, resp, request)
        except ImportError:
            try:
                import boto
                return self._send_boto(boto, resp, request)
            except ImportError:
                stderrlog.info('\nError: boto3 is required for S3 channels. '
                               'Please install with `conda install boto3`\n'
                               'Make sure to run `source deactivate` if you '
                               'are in a conda environment.\n')
                resp.status_code = 404
                return resp

    def close(self):
        pass

    def _send_boto3(self, boto3, resp, request):
        from botocore.exceptions import BotoCoreError, ClientError
        bucket_name, key_string = url_to_s3_info(request.url)

        # Get the key without validation that it exists and that we have
        # permissions to list its contents.
        key = boto3.resource('s3').Object(bucket_name, key_string[1:])

        try:
            response = key.get()
        except (BotoCoreError, ClientError) as exc:
            # This exception will occur if the bucket does not exist or if the
            # user does not have permission to list its contents.
            resp.status_code = 404
            message = {
                "error": "error downloading file from s3",
                "path": request.url,
                "exception": repr(exc),
            }
            fh = SpooledTemporaryFile()
            fh.write(ensure_binary(json.dumps(message)))
            fh.seek(0)
            resp.raw = fh
            resp.close = resp.raw.close
            return resp

        key_headers = response['ResponseMetadata']['HTTPHeaders']
        resp.headers = CaseInsensitiveDict({
            "Content-Type": key_headers.get('content-type', "text/plain"),
            "Content-Length": key_headers['content-length'],
            "Last-Modified": key_headers['last-modified'],
        })

        f = SpooledTemporaryFile()
        key.download_fileobj(f)
        f.seek(0)
        resp.raw = f
        resp.close = resp.raw.close

        return resp

    def _send_boto(self, boto, resp, request):
        conn = boto.connect_s3()

        bucket_name, key_string = url_to_s3_info(request.url)

        # Get the bucket without validation that it exists and that we have
        # permissions to list its contents.
        bucket = conn.get_bucket(bucket_name, validate=False)

        try:
            key = bucket.get_key(key_string)
        except boto.exception.S3ResponseError as exc:
            # This exception will occur if the bucket does not exist or if the
            # user does not have permission to list its contents.
            resp.status_code = 404
            resp.raw = exc
            return resp

        if key and key.exists:
            modified = key.last_modified
            content_type = key.content_type or "text/plain"
            resp.headers = CaseInsensitiveDict({
                "Content-Type": content_type,
                "Content-Length": key.size,
                "Last-Modified": modified,
            })

            fh = SpooledTemporaryFile()
            key.get_contents_to_file(fh)
            fh.seek(0)
            resp.raw = fh
            resp.close = resp.raw.close
        else:
            resp.status_code = 404

        return resp
