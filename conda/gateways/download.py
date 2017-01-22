# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function, unicode_literals

import bz2
import hashlib
import json
from logging import DEBUG, getLogger
from os.path import basename, exists
from textwrap import dedent
from threading import Lock
import warnings

from requests.exceptions import ConnectionError, HTTPError, SSLError
from requests.packages.urllib3.exceptions import InsecureRequestWarning

from .. import CondaError
from .._vendor.auxlib.ish import dals
from .._vendor.auxlib.logz import stringify
from ..base.constants import CONDA_HOMEPAGE_URL
from ..base.context import context
from ..common.compat import ensure_text_type
from ..common.url import join_url
from ..connection import CondaSession
from ..exceptions import (BasicClobberError, CondaHTTPError, CondaRuntimeError, MD5MismatchError,
                          maybe_raise)
from ..models.channel import Channel

log = getLogger(__name__)
stderrlog = getLogger('stderrlog')


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
        # status_code might not exist on SSLError
        help_message = "An HTTP error occurred when trying to retrieve this URL.\n%r" % e
        raise CondaHTTPError(help_message,
                             getattr(e.response, 'url', None),
                             getattr(e.response, 'status_code', None),
                             getattr(e.response, 'reason', None),
                             getattr(e.response, 'elapsed', None))

    finally:
        if content_length:
            getLogger('fetch.stop').info(None)


class Response304ContentUnchanged(Exception):
    pass


def fetch_repodata_remote_request(session, url, etag, mod_stamp):
    if not context.ssl_verify:
        warnings.simplefilter('ignore', InsecureRequestWarning)

    session = session or CondaSession()

    headers = {}
    if etag:
        headers["If-None-Match"] = etag
    if mod_stamp:
        headers["If-Modified-Since"] = mod_stamp

    if 'repo.continuum.io' in url or url.startswith("file://"):
        filename = 'repodata.json.bz2'
        headers['Accept-Encoding'] = 'identity'
    else:
        headers['Accept-Encoding'] = 'gzip, deflate, compress, identity'
        headers['Content-Type'] = 'application/json'
        filename = 'repodata.json'

    try:
        timeout = context.remote_connect_timeout_secs, context.remote_read_timeout_secs
        resp = session.get(join_url(url, filename), headers=headers, proxies=session.proxies,
                           timeout=timeout)
        if log.isEnabledFor(DEBUG):
            log.debug(stringify(resp))
        resp.raise_for_status()

        if resp.status_code == 304:
            raise Response304ContentUnchanged()

        def maybe_decompress(filename, resp_content):
            return ensure_text_type(bz2.decompress(resp_content)
                                    if filename.endswith('.bz2')
                                    else resp_content).strip()
        json_str = maybe_decompress(filename, resp.content)
        fetched_repodata = json.loads(json_str) if json_str else {}
        fetched_repodata['_url'] = url
        add_http_value_to_dict(resp, 'Etag', fetched_repodata, '_etag')
        add_http_value_to_dict(resp, 'Last-Modified', fetched_repodata, '_mod')
        add_http_value_to_dict(resp, 'Cache-Control', fetched_repodata, '_cache_control')
        return fetched_repodata

    except ValueError as e:
        raise CondaRuntimeError("Invalid index file: {0}: {1}".format(join_url(url, filename), e))

    except (ConnectionError, HTTPError, SSLError) as e:
        # status_code might not exist on SSLError
        status_code = getattr(e.response, 'status_code', None)
        if status_code == 404:
            if not url.endswith('/noarch'):
                return None
            else:
                # help_message = dals("""
                # The remote server could not find the channel you requested.
                #
                # As of conda 4.3, a valid channel *must* contain a `noarch/repodata.json` and
                # associated `noarch/repodata.json.bz2` file, even if `noarch/repodata.json` is
                # empty.
                #
                # You will need to adjust your conda configuration to proceed.
                # Use `conda config --show` to view your configuration's current state.
                # Further configuration help can be found at <%s>.
                # """ % join_url(CONDA_HOMEPAGE_URL, 'docs/config.html'))
                help_message = dedent("""
                WARNING: The remote server could not find the noarch directory for the requested
                channel with url: %s

                It is possible you have given conda an invalid channel. Please double-check
                your conda configuration using `conda config --show`.

                If the requested url is in fact a valid conda channel, please request that the
                channel administrator create `noarch/repodata.json` and associated
                `noarch/repodata.json.bz2` files, even if `noarch/repodata.json` is empty.
                """ % url)
                stderrlog.warn(help_message)
                return None

        elif status_code == 403:
            if not url.endswith('/noarch'):
                return None
            else:
                # help_message = dals("""
                # The channel you requested is not available on the remote server.
                #
                # As of conda 4.3, a valid channel *must* contain a `noarch/repodata.json` and
                # associated `noarch/repodata.json.bz2` file, even if `noarch/repodata.json` is
                # empty.
                #
                # You will need to adjust your conda configuration to proceed.
                # Use `conda config --show` to view your configuration's current state.
                # Further configuration help can be found at <%s>.
                # """ % join_url(CONDA_HOMEPAGE_URL, 'docs/config.html'))
                help_message = dedent("""
                WARNING: The remote server could not find the noarch directory for the requested
                channel with url: %s

                It is possible you have given conda an invalid channel. Please double-check
                your conda configuration using `conda config --show`.

                If the requested url is in fact a valid conda channel, please request that the
                channel administrator create `noarch/repodata.json` and associated
                `noarch/repodata.json.bz2` files, even if `noarch/repodata.json` is empty.
                """ % url)
                stderrlog.warn(help_message)
                return None

        elif status_code == 401:
            channel = Channel(url)
            if channel.token:
                help_message = dals("""
                The token '%s' given for the URL is invalid.

                If this token was pulled from anaconda-client, you will need to use
                anaconda-client to reauthenticate.

                If you supplied this token to conda directly, you will need to adjust your
                conda configuration to proceed.

                Use `conda config --show` to view your configuration's current state.
                Further configuration help can be found at <%s>.
               """ % (channel.token, join_url(CONDA_HOMEPAGE_URL, 'docs/config.html')))

            elif context.channel_alias.location in url:
                # Note, this will not trigger if the binstar configured url does
                # not match the conda configured one.
                help_message = dals("""
                The remote server has indicated you are using invalid credentials for this channel.

                If the remote site is anaconda.org or follows the Anaconda Server API, you
                will need to
                  (a) login to the site with `anaconda login`, or
                  (b) provide conda with a valid token directly.

                Further configuration help can be found at <%s>.
               """ % join_url(CONDA_HOMEPAGE_URL, 'docs/config.html'))

            else:
                help_message = dals("""
                The credentials you have provided for this URL are invalid.

                You will need to modify your conda configuration to proceed.
                Use `conda config --show` to view your configuration's current state.
                Further configuration help can be found at <%s>.
                """ % join_url(CONDA_HOMEPAGE_URL, 'docs/config.html'))

        elif status_code is not None and 500 <= status_code < 600:
            help_message = dals("""
            An remote server error occurred when trying to retrieve this URL.

            A 500-type error (e.g. 500, 501, 502, 503, etc.) indicates the server failed to
            fulfill a valid request.  The problem may be spurious, and will resolve itself if you
            try your request again.  If the problem persists, consider notifying the maintainer
            of the remote server.
            """)

        else:
            help_message = "An HTTP error occurred when trying to retrieve this URL.\n%r" % e

        raise CondaHTTPError(help_message,
                             getattr(e.response, 'url', None),
                             status_code,
                             getattr(e.response, 'reason', None),
                             getattr(e.response, 'elapsed', None))


def add_http_value_to_dict(resp, http_key, d, dict_key):
    value = resp.headers.get(http_key)
    if value:
        d[dict_key] = value
