# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function, unicode_literals

from logging import getLogger
from requests import Response
from requests.adapters import BaseAdapter
from requests.structures import CaseInsensitiveDict
from tempfile import mkstemp

from ..disk.delete import rm_rf
from ...common.url import url_to_s3_info

log = getLogger(__name__)
stderrlog = getLogger('stderrlog')


class S3Adapter(BaseAdapter):

    def __init__(self):
        super(S3Adapter, self).__init__()
        self._temp_file = None

    def send(self, request, stream=None, timeout=None, verify=None, cert=None, proxies=None):

        resp = Response()
        resp.status_code = 200
        resp.url = request.url

        try:
            import boto
        except ImportError:
            stderrlog.info('\nError: boto is required for S3 channels. '
                           'Please install it with `conda install boto`\n'
                           'Make sure to run `source deactivate` if you '
                           'are in a conda environment.\n')
            resp.status_code = 404
            return resp

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

            _, self._temp_file = mkstemp()
            key.get_contents_to_filename(self._temp_file)
            f = open(self._temp_file, 'rb')
            resp.raw = f
            resp.close = resp.raw.close
        else:
            resp.status_code = 404

        return resp

    def close(self):
        if self._temp_file:
            rm_rf(self._temp_file)
