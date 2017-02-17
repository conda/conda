# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function, unicode_literals

import hashlib
from logging import getLogger
from os.path import exists, basename
from threading import Lock
import warnings

from requests.exceptions import ConnectionError, HTTPError, SSLError

from .. import CondaError
from .._vendor.auxlib.ish import dals
from ..base.context import context
from ..connection import CondaSession
from ..exceptions import BasicClobberError, CondaHTTPError, MD5MismatchError, maybe_raise

log = getLogger(__name__)


class SingleThreadCondaSession(CondaSession):
    # according to http://stackoverflow.com/questions/18188044/is-the-session-object-from-pythons-requests-library-thread-safe  # NOQA
    # request's Session isn't thread-safe for us

    _session = None
    _mutex = Lock()

    def __init__(self):
        super(SingleThreadCondaSession, self).__init__()

    def __enter__(self):
        session = SingleThreadCondaSession._session
        if session is None:
            session = SingleThreadCondaSession._session = self
        SingleThreadCondaSession._mutex.acquire()
        return session

    def __exit__(self, exc_type, exc_val, exc_tb):
        SingleThreadCondaSession._mutex.release()


def disable_ssl_verify_warning():
    try:
        from requests.packages.urllib3.connectionpool import InsecureRequestWarning
    except ImportError:
        pass
    else:
        warnings.simplefilter('ignore', InsecureRequestWarning)


def download(url, target_full_path, md5sum):
    content_length = None

    if exists(target_full_path):
        maybe_raise(BasicClobberError(target_full_path, url, context), context)

    if not context.ssl_verify:
        disable_ssl_verify_warning()

    try:
        timeout = context.remote_connect_timeout_secs, context.remote_read_timeout_secs
        with SingleThreadCondaSession() as session:
            resp = session.get(url, stream=True, proxies=session.proxies, timeout=timeout)
            resp.raise_for_status()

            content_length = int(resp.headers.get('Content-Length', 0))

            if content_length:
                getLogger('fetch.start').info((basename(target_full_path)[:14], content_length))

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
                            getLogger('fetch.update').info(streamed_bytes)

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

        if md5sum and digest_builder.hexdigest() != md5sum:
            log.debug("MD5 sums mismatch for download: %s (%s != %s), "
                      "trying again" % (url, digest_builder.hexdigest(), md5sum))
            # TODO: refactor this exception
            raise MD5MismatchError("MD5 sums mismatch for download: %s (%s != %s)"
                                   % (url, digest_builder.hexdigest(), md5sum))

    except (ConnectionError, HTTPError, SSLError) as e:
        help_message = dals("""
        An HTTP error occurred when trying to retrieve this URL.
        HTTP errors are often intermittent, and a simple retry will get you on your way.
        %r
        """) % e
        raise CondaHTTPError(help_message,
                             getattr(e.response, 'url', None),
                             getattr(e.response, 'status_code', None),
                             getattr(e.response, 'reason', None),
                             getattr(e.response, 'elapsed', None),
                             e.response)

    finally:
        if content_length:
            getLogger('fetch.stop').info(None)
