# (c) 2012-2015 Continuum Analytics, Inc. / http://continuum.io
# All Rights Reserved
#
# conda is distributed under the terms of the BSD 3-clause license.
# Consult LICENSE.txt or http://opensource.org/licenses/BSD-3-Clause.
from __future__ import absolute_import, division, print_function, unicode_literals

import bz2
import hashlib
import json
import os
import requests
import shutil
import tempfile
import warnings
from functools import wraps
from logging import DEBUG, getLogger
from os.path import basename, dirname, join
from requests.packages.urllib3.connectionpool import InsecureRequestWarning
from warnings import warn

from ._vendor.auxlib.entity import EntityEncoder
from ._vendor.auxlib.ish import dals
from ._vendor.auxlib.logz import stringify
from .base.constants import CONDA_HOMEPAGE_URL
from .base.context import context
from .common.disk import exp_backoff_fn, rm_rf
from .common.url import join_url, maybe_add_auth, url_to_path
from .compat import iteritems, itervalues
from .connection import CondaSession, RETRIES
from .exceptions import CondaHTTPError, CondaRuntimeError, CondaSignatureError, MD5MismatchError
from .install import add_cached_package, dist2pair, find_new_location, package_cache
from .lock import FileLock
from .models.channel import Channel, offline_keep
from .models.record import Record

log = getLogger(__name__)
dotlog = getLogger('dotupdate')
stdoutlog = getLogger('stdoutlog')
stderrlog = getLogger('stderrlog')

fail_unknown_host = False

# for conda-build backward compatibility
handle_proxy_407 = lambda x, y: warn("handle_proxy_407 is deprecated. "
                                     "Now handled by CondaSession.")


def create_cache_dir():
    cache_dir = join(context.pkgs_dirs[0], 'cache')
    try:
        os.makedirs(cache_dir)
    except OSError:
        pass
    return cache_dir


def cache_fn_url(url):
    md5 = hashlib.md5(url.encode('utf-8')).hexdigest()
    return '%s.json' % (md5[:8],)


def add_http_value_to_dict(resp, http_key, d, dict_key):
    value = resp.headers.get(http_key)
    if value:
        d[dict_key] = value

# We need a decorator so that the dot gets printed *after* the repodata is fetched
class dotlog_on_return(object):
    def __init__(self, msg):
        self.msg = msg

    def __call__(self, f):
        @wraps(f)
        def func(*args, **kwargs):
            res = f(*args, **kwargs)
            dotlog.debug("%s args %s kwargs %s" % (self.msg, args, kwargs))
            return res
        return func


@dotlog_on_return("fetching repodata:")
def fetch_repodata(url, cache_dir=None, use_cache=False, session=None):
    if not offline_keep(url):
        return {'packages': {}}
    cache_path = join(cache_dir or create_cache_dir(), cache_fn_url(url))
    try:
        log.debug("Opening repodata cache for %s at %s", url, cache_path)
        with open(cache_path) as f:
            cache = json.load(f)
    except (IOError, ValueError):
        cache = {'packages': {}}

    if use_cache:
        return cache

    if not context.ssl_verify:
        warnings.simplefilter('ignore', InsecureRequestWarning)

    session = session or CondaSession()

    headers = {}
    if "_etag" in cache:
        headers["If-None-Match"] = cache["_etag"]
    if "_mod" in cache:
        headers["If-Modified-Since"] = cache["_mod"]

    if 'repo.continuum.io' in url or url.startswith("file://"):
        filename = 'repodata.json.bz2'
        headers['Accept-Encoding'] = 'identity'
    else:
        headers['Accept-Encoding'] = 'gzip, deflate, compress, identity'
        headers['Content-Type'] = 'application/json'
        filename = 'repodata.json'

    try:
        resp = session.get(join_url(url, filename), headers=headers, proxies=session.proxies,
                           timeout=(3.05, 60))
        if log.isEnabledFor(DEBUG):
            log.debug(stringify(resp))
        resp.raise_for_status()

        if resp.status_code != 304:
            def get_json_str(filename, resp_content):
                if filename.endswith('.bz2'):
                    return bz2.decompress(resp_content).decode('utf-8')
                else:
                    return resp_content.decode('utf-8')

            if url.startswith('file://'):
                file_path = url_to_path(url)
                with FileLock(dirname(file_path)):
                    json_str = get_json_str(filename, resp.content)
            else:
                json_str = get_json_str(filename, resp.content)

            cache = json.loads(json_str)
            add_http_value_to_dict(resp, 'Etag', cache, '_etag')
            add_http_value_to_dict(resp, 'Last-Modified', cache, '_mod')

    except ValueError as e:
        raise CondaRuntimeError("Invalid index file: {0}: {1}".format(join_url(url, filename), e))

    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 404:
            if url.endswith('/noarch'):  # noarch directory might not exist
                return None

            help_message = dals("""
            The remote server could not find the channel you requested.

            You will need to adjust your conda configuration to proceed.
            Use `conda config --show` to view your configuration's current state.
            Further configuration help can be found at <%s>.
            """ % join_url(CONDA_HOMEPAGE_URL, 'docs/config.html'))

        elif e.response.status_code == 403:
            if url.endswith('/noarch'):
                return None
            else:
                help_message = dals("""
                The channel you requested is not available on the remote server.

                You will need to adjust your conda configuration to proceed.
                Use `conda config --show` to view your configuration's current state.
                Further configuration help can be found at <%s>.
                """ % join_url(CONDA_HOMEPAGE_URL, 'docs/config.html'))

        elif e.response.status_code == 401:
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

        elif 500 <= e.response.status_code < 600:
            help_message = dals("""
            An remote server error occurred when trying to retrieve this URL.

            A 500-type error (e.g. 500, 501, 502, 503, etc.) indicates the server failed to
            fulfill a valid request.  The problem may be spurious, and will resolve itself if you
            try your request again.  If the problem persists, consider notifying the maintainer
            of the remote server.
            """)

        else:
            help_message = "An HTTP error occurred when trying to retrieve this URL."

        raise CondaHTTPError(help_message, e.response.url, e.response.status_code,
                             e.response.reason)

    except requests.exceptions.SSLError as e:
        msg = "SSL Error: %s\n" % e
        stderrlog.info("SSL verification error: %s\n" % e)
        log.debug(msg)

    except requests.exceptions.ConnectionError as e:
        msg = "Connection error: %s: %s\n" % (e, url)
        stderrlog.info('Could not connect to %s\n' % url)
        log.debug(msg)
        if fail_unknown_host:
            raise CondaRuntimeError(msg)

        raise CondaRuntimeError(msg)
    cache['_url'] = url
    try:
        with open(cache_path, 'w') as fo:
            json.dump(cache, fo, indent=2, sort_keys=True, cls=EntityEncoder)
    except IOError:
        pass

    return cache or None


def add_unknown(index, priorities):
    priorities = {p[0]: p[1] for p in itervalues(priorities)}
    maxp = max(itervalues(priorities)) + 1 if priorities else 1
    for dist, info in iteritems(package_cache()):
        schannel, dname = dist2pair(dist)
        fname = dname + '.tar.bz2'
        fkey = dist + '.tar.bz2'
        if fkey in index or not info['dirs']:
            continue
        try:
            with open(join(info['dirs'][0], 'info', 'index.json')) as fi:
                meta = Record(**json.load(fi))
        except IOError:
            continue
        if info['urls']:
            url = info['urls'][0]
        elif meta.get('url'):
            url = meta['url']
        elif meta.get('channel'):
            url = meta['channel'].rstrip('/') + '/' + fname
        else:
            url = '<unknown>/' + fname
        if url.rsplit('/', 1)[-1] != fname:
            continue
        channel, schannel2 = Channel(url).url_channel_wtf
        if schannel2 != schannel:
            continue
        priority = priorities.get(schannel, maxp)
        if 'link' in meta:
            del meta['link']
        meta.update({'fn': fname, 'url': url, 'channel': channel,
                     'schannel': schannel, 'priority': priority})
        meta.setdefault('depends', [])
        log.debug("adding cached pkg to index: %s" % fkey)
        index[fkey] = meta


def add_pip_dependency(index):
    for info in itervalues(index):
        if info['name'] == 'python' and info['version'].startswith(('2.', '3.')):
            info['depends'] = info['depends'] + ('pip',)


def fetch_index(channel_urls, use_cache=False, unknown=False, index=None):
    log.debug('channel_urls=' + repr(channel_urls))
    # pool = ThreadPool(5)
    if index is None:
        index = {}
    if not context.json:
        stdoutlog.info("Fetching package metadata ...")

    urls = tuple(filter(offline_keep, channel_urls))
    try:
        import concurrent.futures
        executor = concurrent.futures.ThreadPoolExecutor(10)
    except (ImportError, RuntimeError) as e:
        # concurrent.futures is only available in Python >= 3.2 or if futures is installed
        # RuntimeError is thrown if number of threads are limited by OS
        log.debug(repr(e))
        session = CondaSession()
        repodatas = [(url, fetch_repodata(url, use_cache=use_cache, session=session))
                     for url in urls]
    else:
        try:
            futures = tuple(executor.submit(fetch_repodata, url, use_cache=use_cache,
                                            session=CondaSession()) for url in urls)
            repodatas = [(u, f.result()) for u, f in zip(urls, futures)]
        except RuntimeError as e:
            # Cannot start new thread, then give up parallel execution
            log.debug(repr(e))
            session = CondaSession()
            repodatas = [(url, fetch_repodata(url, use_cache=use_cache, session=session))
                         for url in urls]
        finally:
            executor.shutdown(wait=True)

    def make_index(repodatas):
        result = dict()
        for channel_url, repodata in repodatas:
            if repodata is None:
                continue
            canonical_name, priority = channel_urls[channel_url]
            channel = Channel(channel_url)
            for fn, info in iteritems(repodata['packages']):
                full_url = join_url(channel_url, fn)
                info.update(dict(fn=fn,
                                 schannel=canonical_name,
                                 channel=channel_url,
                                 priority=priority,
                                 url=full_url,
                                 auth=channel.auth,
                                 ))
                key = canonical_name + '::' + fn if canonical_name != 'defaults' else fn
                result[key] = Record(**info)
        return result

    index = make_index(repodatas)

    if not context.json:
        stdoutlog.info('\n')
    if unknown:
        add_unknown(index, channel_urls)
    if context.add_pip_as_python_dependency:
        add_pip_dependency(index)
    return index


def fetch_pkg(info, dst_dir=None, session=None):
    '''
    fetch a package given by `info` and store it into `dst_dir`
    '''

    session = session or CondaSession()

    fn = info['fn']
    url = info.get('url') or info['channel'] + '/' + fn
    url = maybe_add_auth(url, info.get('auth'))
    log.debug("url=%r" % url)

    if dst_dir is None:
        dst_dir = find_new_location(fn[:-8])[0]
    path = join(dst_dir, fn)

    download(url, path, session=session, md5=info['md5'], urlstxt=True)
    if info.get('sig'):
        from .signature import verify

        fn2 = fn + '.sig'
        url = (info['channel'] if info['sig'] == '.' else
               info['sig'].rstrip('/')) + '/' + fn2
        log.debug("signature url=%r" % url)
        download(url, join(dst_dir, fn2), session=session)
        try:
            if verify(path):
                return
        except CondaSignatureError:
            raise

        raise CondaSignatureError("Error: Signature for '%s' is invalid." % (basename(path)))


def download(url, dst_path, session=None, md5=None, urlstxt=False, retries=None):
    assert "::" not in str(dst_path), str(dst_path)
    if not offline_keep(url):
        raise RuntimeError("Cannot download in offline mode: %s" % (url,))

    pp = dst_path + '.part'
    dst_dir = dirname(dst_path)
    session = session or CondaSession()

    if not context.ssl_verify:
        try:
            from requests.packages.urllib3.connectionpool import InsecureRequestWarning
        except ImportError:
            pass
        else:
            warnings.simplefilter('ignore', InsecureRequestWarning)

    if retries is None:
        retries = RETRIES

    with FileLock(dst_path):
        rm_rf(dst_path)
        try:
            resp = session.get(url, stream=True, proxies=session.proxies, timeout=(3.05, 27))
            resp.raise_for_status()
        except requests.exceptions.HTTPError as e:
            msg = "HTTPError: %s: %s\n" % (e, url)
            log.debug(msg)
            raise CondaRuntimeError(msg)

        except requests.exceptions.ConnectionError as e:
            msg = "Connection error: %s: %s\n" % (e, url)
            stderrlog.info('Could not connect to %s\n' % url)
            log.debug(msg)
            raise CondaRuntimeError(msg)

        except IOError as e:
            raise CondaRuntimeError("Could not open '%s': %s" % (url, e))

        size = resp.headers.get('Content-Length')
        if size:
            size = int(size)
            fn = basename(dst_path)
            getLogger('fetch.start').info((fn[:14], size))

        if md5:
            h = hashlib.new('md5')
        try:
            with open(pp, 'wb') as fo:
                index = 0
                for chunk in resp.iter_content(2**14):
                    index += len(chunk)
                    try:
                        fo.write(chunk)
                    except IOError:
                        raise CondaRuntimeError("Failed to write to %r." % pp)

                    if md5:
                        h.update(chunk)

                    if size and 0 <= index <= size:
                        getLogger('fetch.update').info(index)

        except IOError as e:
            if e.errno == 104 and retries:  # Connection reset by pee
                # try again
                log.debug("%s, trying again" % e)
                return download(url, dst_path, session=session, md5=md5,
                                urlstxt=urlstxt, retries=retries - 1)
            raise CondaRuntimeError("Could not open %r for writing (%s)." % (pp, e))

        if size:
            getLogger('fetch.stop').info(None)

        if md5 and h.hexdigest() != md5:
            if retries:
                # try again
                log.debug("MD5 sums mismatch for download: %s (%s != %s), "
                          "trying again" % (url, h.hexdigest(), md5))
                return download(url, dst_path, session=session, md5=md5,
                                urlstxt=urlstxt, retries=retries - 1)
            raise MD5MismatchError("MD5 sums mismatch for download: %s (%s != %s)"
                                   % (url, h.hexdigest(), md5))

        try:
            exp_backoff_fn(os.rename, pp, dst_path)
        except OSError as e:
            raise CondaRuntimeError("Could not rename %r to %r: %r" %
                                    (pp, dst_path, e))

        if urlstxt:
            add_cached_package(dst_dir, url, overwrite=True, urlstxt=True)


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
            if self.verbose:
                from .console import setup_handlers
                setup_handlers()
            self.tmp_dir = tempfile.mkdtemp()
            dst = join(self.tmp_dir, basename(self.url))
            download(self.url, dst)
            return dst

    def __exit__(self, exc_type, exc_value, traceback):
        if self.tmp_dir:
            shutil.rmtree(self.tmp_dir)
