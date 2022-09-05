# -*- coding: utf-8 -*-
# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
from __future__ import absolute_import, division, print_function, unicode_literals

import json
from logging import LoggerAdapter, getLogger
import os
import re
from tempfile import SpooledTemporaryFile

have_boto3 = have_boto = False
try:
    import boto3
    have_boto3 = True
except ImportError:
    try:
        import boto
        have_boto = True
    except ImportError:
        pass

from .. import BaseAdapter, CaseInsensitiveDict, Response
from ....common.compat import ensure_binary
from ....common.url import urlparse, url_to_s3_info

log = getLogger(__name__)
stderrlog = LoggerAdapter(getLogger('conda.stderrlog'), extra=dict(terminator="\n"))


class OSSAdapter(BaseAdapter):

    def __init__(self):
        super(OSSAdapter, self).__init__()
        endpoint = os.getenv("H2H_MIRROR_ENDPOINT", os.getenv("ALIYUN_ENDPOINT", 'http://oss-cn-shanghai.aliyuncs.com'))
        if not re.match(r'[a-z][a-z0-9]{0,11}://', endpoint):
            endpoint = f'http://{endpoint}'
        self._endpoint = endpoint
        http_proxy = os.environ.get("all_proxy") or os.environ.get("HTTP_PROXY") or os.environ.get("http_proxy")
        https_proxy = os.environ.get("ALL_PROXY") or os.environ.get("HTTPS_PROXY") or os.environ.get("https_proxy")
        self._proxies = {}
        if http_proxy and len(http_proxy) > 0:
            self._proxies["http_proxy"] = http_proxy
        if https_proxy and len(https_proxy) > 0:
            self._proxies["https_proxy"] = https_proxy

    def send(self, request, stream=None, timeout=None, verify=None, cert=None, proxies=None):
        resp = Response()
        resp.status_code = 200
        resp.url = request.url
        if have_boto3:
            return self._send_boto3(boto3, resp, request)
        elif have_boto:
            return self._send_boto(boto, resp, request)
        else:
            stderrlog.info('\nError: boto3 is required for S3 channels. '
                           'Please install with `conda install boto3`\n'
                           'Make sure to run `source deactivate` if you '
                           'are in a conda environment.\n')
            resp.status_code = 404
            return resp

    def close(self):
        pass

    def _send_by_ram_role(self, bucket_name, key_string):
        try:
            import requests, oss2
            with open(os.path.expanduser('~/.aliyun/config.json'), 'r') as f:
                profile = json.load(f)
                for p in profile["profiles"]:
                    if p["name"] == profile["current"]:
                        ram_role = p["ram_role_name"]
            credentials = requests.get(
                url=f"http://100.100.100.200/latest/meta-data/ram/security-credentials/{ram_role}",
                proxies=self._proxies).json()
            if credentials["Code"] != "Success":
                raise ValueError("\nCan not get STS token.")
            auth = oss2.StsAuth(
                credentials["AccessKeyId"],
                credentials["AccessKeySecret"],
                credentials["SecurityToken"]
            )
            bucket = oss2.Bucket(auth, self._endpoint, bucket_name, proxies=self._proxies)
            headers = bucket.head_object(key_string[1:])
            fh = SpooledTemporaryFile()
            resp = bucket.get_object(key_string[1:])
            fh.write(resp.read())
            fh.seek(0)
        except Exception as e:
            raise ValueError(f"\nCan not send using ram role.\n{e}")
        return fh, headers.headers

    def url_to_oss_info(self, url):
        """Convert an oss url to a tuple of bucket and key.

        Examples:
            >>> url_to_oss_info("oss://bucket-name.bucket/here/is/the/key")
            ('bucket-name.bucket', '/here/is/the/key')
        """
        parsed_url = urlparse(url)
        assert parsed_url.scheme == 'oss', "You can only use oss: urls (not %r)" % url
        bucket, key = parsed_url.hostname, parsed_url.path
        return bucket, key

    def _send_boto3(self, boto3, resp, request):
        from botocore.exceptions import BotoCoreError, ClientError
        bucket_name, key_string = self.url_to_oss_info(request.url)
        # https://github.com/conda/conda/issues/8993
        # creating a separate boto3 session to make this thread safe
        session = boto3.session.Session(profile_name='aliyun')
        # create a resource client using this thread's session object
        if self._proxies and len(self._proxies) > 0:
            s3 = session.resource('s3', endpoint_url=self._endpoint, config=boto3.session.Config(
                s3={'addressing_style': 'virtual'},
                proxies=self._proxies,
            ))
        else:
            s3 = session.resource('s3', endpoint_url=self._endpoint, config=boto3.session.Config(
                s3={'addressing_style': 'virtual'},
            ))
        # finally get the S3 object
        key = s3.Object(bucket_name, key_string[1:])
        try:
            response = key.get()
        except (BotoCoreError, ClientError) as e:
            try:
                response, key_headers = self._send_by_ram_role(bucket_name, key_string)
                resp.headers = CaseInsensitiveDict({
                    "Content-Type": key_headers.get('content-type', "text/plain"),
                    "Content-Length": key_headers['content-length'],
                    "Last-Modified": key_headers['last-modified'],
                })

                resp.raw = response
                resp.close = resp.raw.close

                return resp
            except:
                resp.status_code = 404
                message = {
                    "error": "error downloading file from oss",
                    "path": request.url,
                    "exception": repr(e),
                }
                resp.raw = self._write_tempfile(lambda x: x.write(ensure_binary(json.dumps(message))))
                resp.close = resp.raw.close
                return resp

        key_headers = response['ResponseMetadata']['HTTPHeaders']
        resp.headers = CaseInsensitiveDict({
            "Content-Type": key_headers.get('content-type', "text/plain"),
            "Content-Length": key_headers['content-length'],
            "Last-Modified": key_headers['last-modified'],
        })
        print(resp.headers)

        resp.raw = self._write_tempfile(key.download_fileobj)
        resp.close = resp.raw.close

        return resp

    def _send_boto(self, boto, resp, request):
        conn = boto.connect_s3()

        bucket_name, key_string = url_to_s3_info(request.url)
        bucket = conn.get_bucket(bucket_name, validate=False)
        try:
            key = bucket.get_key(key_string)
        except boto.exception.S3ResponseError as exc:
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

            resp.raw = self._write_tempfile(key.get_contents_to_file)
            resp.close = resp.raw.close
        else:
            resp.status_code = 404

        return resp

    def _write_tempfile(self, writer_callable):
        fh = SpooledTemporaryFile()
        writer_callable(fh)
        fh.seek(0)
        return fh
