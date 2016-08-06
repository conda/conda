# (c) 2012-2015 Continuum Analytics, Inc. / http://continuum.io
# All Rights Reserved
#
# conda is distributed under the terms of the BSD 3-clause license.
# Consult LICENSE.txt or http://opensource.org/licenses/BSD-3-Clause.
from __future__ import print_function, division, absolute_import, unicode_literals

import bz2
import getpass
import hashlib
import json
import os
import requests
import shutil
import tempfile
import warnings
from functools import wraps
from logging import getLogger, DEBUG
from os.path import basename, dirname, join
from requests.packages.urllib3.connectionpool import InsecureRequestWarning

from ._vendor.auxlib.logz import stringify
from .base.context import context
from .common.url import add_username_and_pass_to_url, url_to_path
from .compat import itervalues, input, iteritems
from .connection import CondaSession, RETRIES
from .models.channel import Channel, offline_keep
from .exceptions import (ProxyError, CondaRuntimeError, CondaSignatureError, CondaHTTPError)
from .install import add_cached_package, find_new_location, package_cache, dist2pair, rm_rf
from .lock import FileLock
from .utils import exp_backoff_fn, memoized
from math import floor
log = getLogger(__name__)
dotlog = getLogger('dotupdate')
stdoutlog = getLogger('stdoutlog')
stderrlog = getLogger('stderrlog')

fail_unknown_host = False


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
        resp = session.get(url + filename, headers=headers, proxies=session.proxies,
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
        raise CondaRuntimeError("Invalid index file: {0}{1}: {2}"
                                .format(url, filename, e))

    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 407:  # Proxy Authentication Required
            handle_proxy_407(url, session)
            # Try again
            return fetch_repodata(url, cache_dir=cache_dir, use_cache=use_cache, session=session)

        if e.response.status_code == 404:
            if url.endswith('/noarch/'):  # noarch directory might not exist
                return None
            msg = 'Could not find URL: %s' % url
        elif e.response.status_code == 403 and url.endswith('/noarch/'):
            return None

        elif e.response.status_code == 401 and context.channel_alias in url:
            # Note, this will not trigger if the binstar configured url does
            # not match the conda configured one.
            msg = ("Warning: you may need to login to anaconda.org again with "
                   "'anaconda login' to access private packages(%s, %s)" %
                   (url, e))
            stderrlog.info(msg)
            return fetch_repodata(url, cache_dir=cache_dir, use_cache=use_cache, session=session)

        else:
            msg = "HTTPError: %s: %s\n" % (e, url)

        log.debug(msg)
        raise CondaHTTPError(msg)

    except requests.exceptions.SSLError as e:
        msg = "SSL Error: %s\n" % e
        stderrlog.info("SSL verification error: %s\n" % e)
        log.debug(msg)

    except requests.exceptions.ConnectionError as e:
        # requests isn't so nice here. For whatever reason, https gives this
        # error and http gives the above error. Also, there is no status_code
        # attribute here. We have to just check if it looks like 407.  See
        # https://github.com/kennethreitz/requests/issues/2061.
        if "407" in str(e):  # Proxy Authentication Required
            handle_proxy_407(url, session)
            # Try again
            return fetch_repodata(url, cache_dir=cache_dir, use_cache=use_cache, session=session)
        msg = "Connection error: %s: %s\n" % (e, url)
        stderrlog.info('Could not connect to %s\n' % url)
        log.debug(msg)
        if fail_unknown_host:
            raise CondaRuntimeError(msg)

        raise CondaRuntimeError(msg)
    cache['_url'] = url
    try:
        with open(cache_path, 'w') as fo:
            json.dump(cache, fo, indent=2, sort_keys=True)
    except IOError:
        pass

    return cache or None


def handle_proxy_407(url, session):
    """
    Prompts the user for the proxy username and password and modifies the
    proxy in the session object to include it.
    """
    # We could also use HTTPProxyAuth, but this does not work with https
    # proxies (see https://github.com/kennethreitz/requests/issues/2061).
    scheme = requests.packages.urllib3.util.url.parse_url(url).scheme
    if scheme not in session.proxies:
        raise ProxyError("""Could not find a proxy for %r. See
http://conda.pydata.org/docs/html#configure-conda-for-use-behind-a-proxy-server
for more information on how to configure proxies.""" % scheme)
    username, passwd = get_proxy_username_and_pass(scheme)
    session.proxies[scheme] = add_username_and_pass_to_url(
                            session.proxies[scheme], username, passwd)


@memoized
def get_proxy_username_and_pass(scheme):
    username = input("\n%s proxy username: " % scheme)
    passwd = getpass.getpass("Password:")
    return username, passwd

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
                meta = json.load(fi)
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
        if (info['name'] == 'python' and
                info['version'].startswith(('2.', '3.'))):
            info.setdefault('depends', []).append('pip')

def fetch_index(channel_urls, use_cache=False, unknown=False, index=None):
    log.debug('channel_urls=' + repr(channel_urls))
    # pool = ThreadPool(5)
    if index is None:
        index = {}
    stdoutlog.info("Fetching package metadata ...")
    # if not isinstance(channel_urls, dict):
    #     channel_urls = prioritize_channels(channel_urls)

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

    for channel, repodata in repodatas:
        if repodata is None:
            continue
        new_index = repodata['packages']
        url_s, priority = channel_urls[channel]
        channel = channel.rstrip('/')
        for fn, info in iteritems(new_index):
            info['fn'] = fn
            info['schannel'] = url_s
            info['channel'] = channel
            info['priority'] = priority
            info['url'] = channel + '/' + fn
            key = url_s + '::' + fn if url_s != 'defaults' else fn
            index[key] = info

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
    url = info.get('url')
    if url is None:
        url = info['channel'] + '/' + fn
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

        raise CondaSignatureError("Error: Signature for '%s' is invalid." %
                                  (basename(path)))


def download(url, dst_path, session=None, md5=None, urlstxt=False, retries=None):
    assert "::" not in str(url), url
    assert "::" not in str(dst_path), str(dst_path)
    from .instructions import update_bar, bar_length
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
            if e.response.status_code == 407:  # Proxy Authentication Required
                handle_proxy_407(url, session)
                # Try again
                return download(url, dst_path, session=session, md5=md5,
                                urlstxt=urlstxt, retries=retries)
            msg = "HTTPError: %s: %s\n" % (e, url)
            log.debug(msg)
            raise CondaRuntimeError(msg)

        except requests.exceptions.ConnectionError as e:
            # requests isn't so nice here. For whatever reason, https gives
            # this error and http gives the above error. Also, there is no
            # status_code attribute here.  We have to just check if it looks
            # like 407.
            # See: https://github.com/kennethreitz/requests/issues/2061.
            if "407" in str(e):  # Proxy Authentication Required
                handle_proxy_407(url, session)
                # try again
                return download(url, dst_path, session=session, md5=md5,
                                urlstxt=urlstxt, retries=retries)
            msg = "Connection error: %s: %s\n" % (e, url)
            stderrlog.info('Could not connect to %s\n' % url)
            log.debug(msg)
            raise CondaRuntimeError(msg)

        except IOError as e:
            raise CondaRuntimeError("Could not open '%s': %s" % (url, e))

        size = resp.headers.get('Content-Length')
        if size:
            size = int(size)

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

                    if size and 0 <= index <= size and url in update_bar:
                        tmp = floor(float(index / size) * bar_length)
                        if tmp > bar_length:
                            update_bar[url].value = 100
                        else:
                            update_bar[url].value = tmp

        except IOError as e:
            if e.errno == 104 and retries:  # Connection reset by pee
                # try again
                log.debug("%s, trying again" % e)
                return download(url, dst_path, session=session, md5=md5,
                                urlstxt=urlstxt, retries=retries - 1)
            raise CondaRuntimeError("Could not open %r for writing (%s)." % (pp, e))

        if md5 and h.hexdigest() != md5:
            if retries:
                # try again
                log.debug("MD5 sums mismatch for download: %s (%s != %s), "
                          "trying again" % (url, h.hexdigest(), md5))
                return download(url, dst_path, session=session, md5=md5,
                                urlstxt=urlstxt, retries=retries - 1)
            raise CondaRuntimeError("MD5 sums mismatch for download: %s (%s != %s)"
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
