# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function, unicode_literals

import hashlib
from logging import DEBUG, getLogger
from os.path import basename, exists, join
import tempfile
import warnings

from . import ConnectionError, HTTPError, InsecureRequestWarning, InvalidSchema, SSLError
from .session import CondaSession
from ..disk.delete import rmtree
from ... import CondaError
from ..._vendor.auxlib.ish import dals
from ..._vendor.auxlib.logz import stringify
from ...base.context import context
from ...common.compat import text_type
from ...common.io import time_recorder
from ...exceptions import (BasicClobberError, CondaDependencyError, CondaHTTPError,
                           MD5MismatchError, maybe_raise)

log = getLogger(__name__)


def disable_ssl_verify_warning():
    warnings.simplefilter('ignore', InsecureRequestWarning)


@time_recorder("download")
def download(url, target_full_path, md5sum, progress_update_callback=None):
    # TODO: For most downloads, we should know the size of the artifact from what's reported
    #       in repodata.  We should validate that here also, in addition to the 'Content-Length'
    #       header.
    if exists(target_full_path):
        maybe_raise(BasicClobberError(target_full_path, url, context), context)

    if not context.ssl_verify:
        disable_ssl_verify_warning()

    try:
        timeout = context.remote_connect_timeout_secs, context.remote_read_timeout_secs
        session = CondaSession()
        resp = session.get(url, stream=True, proxies=session.proxies, timeout=timeout)
        if log.isEnabledFor(DEBUG):
            log.debug(stringify(resp))
        resp.raise_for_status()

        content_length = int(resp.headers.get('Content-Length', 0))

        digest_builder = hashlib.new('md5')
        try:
            with open(target_full_path, 'wb') as fh:
                streamed_bytes = 0
                for chunk in resp.iter_content(2 ** 14):
                    # chunk could be the decompressed form of the real data
                    # but we want the exact number of bytes read till now
                    streamed_bytes = resp.raw.tell()
                    try:
                        fh.write(chunk)
                    except IOError as e:
                        message = "Failed to write to %(target_path)s\n  errno: %(errno)d"
                        # TODO: make this CondaIOError
                        raise CondaError(message, target_path=target_full_path, errno=e.errno)

                    digest_builder.update(chunk)

                    if content_length and 0 <= streamed_bytes <= content_length:
                        if progress_update_callback:
                            progress_update_callback(streamed_bytes / content_length)

            if content_length and streamed_bytes != content_length:
                # TODO: needs to be a more-specific error type
                message = dals("""
                Downloaded bytes did not match Content-Length
                  url: %(url)s
                  target_path: %(target_path)s
                  Content-Length: %(content_length)d
                  downloaded bytes: %(downloaded_bytes)d
                """)
                raise CondaError(message, url=url, target_path=target_full_path,
                                 content_length=content_length,
                                 downloaded_bytes=streamed_bytes)

        except (IOError, OSError) as e:
            if e.errno == 104:
                # Connection reset by peer
                log.debug("%s, trying again" % e)
            raise

        actual_md5sum = digest_builder.hexdigest()
        if md5sum and actual_md5sum != md5sum:
            log.debug("MD5 sums mismatch for download: %s (%s != %s), "
                      "trying again" % (url, digest_builder.hexdigest(), md5sum))
            raise MD5MismatchError(url, target_full_path, md5sum, actual_md5sum)

    except InvalidSchema as e:
        if 'SOCKS' in text_type(e):
            message = dals("""
                Requests has identified that your current working environment is configured
                to use a SOCKS proxy, but pysocks is not installed.  To proceed, remove your
                proxy configuration, run `conda install pysocks`, and then you can re-enable
                your proxy configuration.
                """)
            raise CondaDependencyError(message)
        else:
            raise

    except (ConnectionError, HTTPError, SSLError) as e:
        help_message = dals("""
        An HTTP error occurred when trying to retrieve this URL.
        HTTP errors are often intermittent, and a simple retry will get you on your way.
        """)
        raise CondaHTTPError(help_message,
                             url,
                             getattr(e.response, 'status_code', None),
                             getattr(e.response, 'reason', None),
                             getattr(e.response, 'elapsed', None),
                             e.response,
                             caused_by=e)


class TmpDownload(object):
    """
    Context manager to handle downloads to a tempfile
    """
    def __init__(self, url, verbose=True):
        self.url = url
        self.verbose = verbose

    def __enter__(self):
        if '://' not in self.url:
            # if we provide the file itself, no tmp dir is created
            self.tmp_dir = None
            return self.url
        else:
            self.tmp_dir = tempfile.mkdtemp()
            dst = join(self.tmp_dir, basename(self.url))
            download(self.url, dst, None)
            return dst

    def __exit__(self, exc_type, exc_value, traceback):
        if self.tmp_dir:
            rmtree(self.tmp_dir)
