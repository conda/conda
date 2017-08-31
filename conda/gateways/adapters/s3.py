# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function, unicode_literals

import json
from logging import getLogger
from tempfile import SpooledTemporaryFile

from requests import Response
from requests.adapters import BaseAdapter
from requests.structures import CaseInsensitiveDict

from ...common.compat import ensure_binary
from ...common.url import url_to_s3_info

log = getLogger(__name__)
stderrlog = getLogger('stderrlog')


class S3Adapter(BaseAdapter):

    def __init__(self):
        super(S3Adapter, self).__init__()

    def send(self, request, stream=None, timeout=None, verify=None, cert=None, proxies=None):

        resp = Response()
        resp.status_code = 200
        resp.url = request.url

        try:
            import boto3
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
        except ImportError:
            stderrlog.info('\nError: boto3 is required for S3 channels. '
                           'Please install with `conda install boto3`\n'
                           'Make sure to run `source deactivate` if you '
                           'are in a conda environment.\n')
            resp.status_code = 404
            return resp

