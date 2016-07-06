# (c) 2012-2015 Continuum Analytics, Inc. / http://continuum.io
# All Rights Reserved
#
# conda is distributed under the terms of the BSD 3-clause license.
# Consult LICENSE.txt or http://opensource.org/licenses/BSD-3-Clause.
from __future__ import print_function, division, absolute_import

import bz2
import getpass
import hashlib
import json
import os
import shutil
import tempfile
import warnings
from functools import wraps
from logging import getLogger
from os.path import basename, dirname, join

from ._vendor.requests.exceptions import SSLError, HTTPError
from ._vendor.requests.packages.urllib3.connection import ConnectionError
from ._vendor.requests.packages.urllib3.exceptions import InsecureRequestWarning
from ._vendor.requests.packages.urllib3.util import parse_url
from .compat import itervalues, input, urllib_quote, iterkeys, iteritems
from .config import (pkgs_dirs, DEFAULT_CHANNEL_ALIAS, remove_binstar_tokens,
                     hide_binstar_tokens, allowed_channels, add_pip_as_python_dependency,
                     ssl_verify, rc, prioritize_channels, url_channel)
from .connection import CondaSession, unparse_url, RETRIES
from .install import (add_cached_package, find_new_location, package_cache, dist2pair,
                      rm_rf, exp_backoff_fn)
from .lock import Locked
from .utils import memoized
from .exceptions import ProxyError, ChannelNotAllowed


log = getLogger(__name__)
dotlog = getLogger('dotupdate')
stdoutlog = getLogger('stdoutlog')
stderrlog = getLogger('stderrlog')

fail_unknown_host = False


def create_cache_dir():
    cache_dir = join(pkgs_dirs[0], 'cache')
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
    cache_path = join(cache_dir or create_cache_dir(), cache_fn_url(url))
    try:
        with open(cache_path) as f:
            cache = json.load(f)
    except (IOError, ValueError):
        cache = {'packages': {}}

    if use_cache:
        return cache

    if not ssl_verify:
        try:
            InsecureRequestWarning
        except ImportError:
            pass
        else:
            warnings.simplefilter('ignore', InsecureRequestWarning)

    session = session or CondaSession()

    headers = {}
    if "_etag" in cache:
        headers["If-None-Match"] = cache["_etag"]
    if "_mod" in cache:
        headers["If-Modified-Since"] = cache["_mod"]

    if 'repo.continuum.io' in url or url.startswith("file://"):
        filename = 'repodata.json.bz2'
    else:
        headers['Accept-Encoding'] = 'gzip, deflate, compress, identity'
        headers['Content-Type'] = 'application/json'
        filename = 'repodata.json'

    try:
        resp = session.get(url + filename, headers=headers, proxies=session.proxies)
        resp.raise_for_status()
        if resp.status_code != 304:
            if filename.endswith('.bz2'):
                json_str = bz2.decompress(resp.content).decode('utf-8')
            else:
                json_str = resp.content.decode('utf-8')
            cache = json.loads(json_str)
            add_http_value_to_dict(resp, 'Etag', cache, '_etag')
            add_http_value_to_dict(resp, 'Last-Modified', cache, '_mod')

    except ValueError as e:
        raise RuntimeError("Invalid index file: {0}{1}: {2}"
                           .format(remove_binstar_tokens(url), filename, e))

    except HTTPError as e:
        if e.response.status_code == 407:  # Proxy Authentication Required
            handle_proxy_407(url, session)
            # Try again
            return fetch_repodata(url, cache_dir=cache_dir, use_cache=use_cache, session=session)

        if e.response.status_code == 404:
            if url.startswith(DEFAULT_CHANNEL_ALIAS):
                user = remove_binstar_tokens(url) \
                             .split(DEFAULT_CHANNEL_ALIAS)[1] \
                             .split("/")[0]
                msg = 'Could not find anaconda.org user %s' % user
            else:
                if url.endswith('/noarch/'):  # noarch directory might not exist
                    return None
                msg = 'Could not find URL: %s' % remove_binstar_tokens(url)
        elif e.response.status_code == 403 and url.endswith('/noarch/'):
            return None

        elif (e.response.status_code == 401 and
                rc.get('channel_alias', DEFAULT_CHANNEL_ALIAS) in url):
            # Note, this will not trigger if the binstar configured url does
            # not match the conda configured one.
            msg = ("Warning: you may need to login to anaconda.org again with "
                   "'anaconda login' to access private packages(%s, %s)" %
                   (hide_binstar_tokens(url), e))
            stderrlog.info(msg)
            return fetch_repodata(remove_binstar_tokens(url),
                                  cache_dir=cache_dir,
                                  use_cache=use_cache, session=session)

        else:
            msg = "HTTPError: %s: %s\n" % (e, remove_binstar_tokens(url))

        log.debug(msg)
        raise RuntimeError(msg)

    except SSLError as e:
        msg = "SSL Error: %s\n" % e
        stderrlog.info("SSL verification error: %s\n" % e)
        log.debug(msg)

    except ConnectionError as e:
        # requests isn't so nice here. For whatever reason, https gives this
        # error and http gives the above error. Also, there is no status_code
        # attribute here. We have to just check if it looks like 407.  See
        # https://github.com/kennethreitz/requests/issues/2061.
        if "407" in str(e):  # Proxy Authentication Required
            handle_proxy_407(url, session)
            # Try again
            return fetch_repodata(url, cache_dir=cache_dir, use_cache=use_cache, session=session)

        msg = "Connection error: %s: %s\n" % (e, remove_binstar_tokens(url))
        stderrlog.info('Could not connect to %s\n' % remove_binstar_tokens(url))
        log.debug(msg)
        if fail_unknown_host:
            raise RuntimeError(msg)

    cache['_url'] = remove_binstar_tokens(url)
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
    scheme = parse_url(url).scheme
    if scheme not in session.proxies:
        raise ProxyError("""Could not find a proxy for %r. See
http://conda.pydata.org/docs/html#configure-conda-for-use-behind-a-proxy-server
for more information on how to configure proxies.""" % scheme)
    username, passwd = get_proxy_username_and_pass(scheme)
    session.proxies[scheme] = add_username_and_pass_to_url(
                            session.proxies[scheme], username, passwd)

def add_username_and_pass_to_url(url, username, passwd):
    urlparts = list(parse_url(url))
    passwd = urllib_quote(passwd, '')
    urlparts[1] = username + ':' + passwd
    return unparse_url(urlparts)

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
        channel, schannel2 = url_channel(url)
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
    if not isinstance(channel_urls, dict):
        channel_urls = prioritize_channels(channel_urls)
    for url in iterkeys(channel_urls):
        if allowed_channels and url not in allowed_channels:
            raise ChannelNotAllowed("""
Error: URL '%s' not in allowed channels.

Allowed channels are:
  - %s
""" % (url, '\n  - '.join(allowed_channels)))

    try:
        import concurrent.futures
        executor = concurrent.futures.ThreadPoolExecutor(10)
    except (ImportError, RuntimeError):
        # concurrent.futures is only available in Python >= 3.2 or if futures is installed
        # RuntimeError is thrown if number of threads are limited by OS
        session = CondaSession()
        repodatas = [(url, fetch_repodata(url, use_cache=use_cache, session=session))
                     for url in iterkeys(channel_urls)]
    else:
        try:
            urls = tuple(channel_urls)
            futures = tuple(executor.submit(fetch_repodata, url, use_cache=use_cache,
                                            session=CondaSession()) for url in urls)
            repodatas = [(u, f.result()) for u, f in zip(urls, futures)]
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
    if add_pip_as_python_dependency:
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
        from .signature import verify, SignatureError

        fn2 = fn + '.sig'
        url = (info['channel'] if info['sig'] == '.' else
               info['sig'].rstrip('/')) + '/' + fn2
        log.debug("signature url=%r" % url)
        download(url, join(dst_dir, fn2), session=session)
        try:
            if verify(path):
                return
        except SignatureError:
            raise

        raise SignatureError("Error: Signature for '%s' is invalid." %
                             (basename(path)))


def download(url, dst_path, session=None, md5=None, urlstxt=False,
             retries=None):
    pp = dst_path + '.part'
    dst_dir = dirname(dst_path)
    session = session or CondaSession()

    if not ssl_verify:
        try:
            from requests.packages.urllib3.connectionpool import InsecureRequestWarning
        except ImportError:
            pass
        else:
            warnings.simplefilter('ignore', InsecureRequestWarning)

    if retries is None:
        retries = RETRIES
    with Locked(dst_dir):

        rm_rf(dst_path)

        try:
            resp = session.get(url, stream=True, proxies=session.proxies)
            resp.raise_for_status()
        except HTTPError as e:
            if e.response.status_code == 407:  # Proxy Authentication Required
                handle_proxy_407(url, session)
                # Try again
                return download(url, dst_path, session=session, md5=md5,
                                urlstxt=urlstxt, retries=retries)
            msg = "HTTPError: %s: %s\n" % (e, url)
            log.debug(msg)
            raise RuntimeError(msg)

        except ConnectionError as e:
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
            raise RuntimeError(msg)

        except IOError as e:
            raise RuntimeError("Could not open '%s': %s" % (url, e))

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
                        raise RuntimeError("Failed to write to %r." % pp)

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
            raise RuntimeError("Could not open %r for writing (%s)." % (pp, e))

        if size:
            getLogger('fetch.stop').info(None)

        if md5 and h.hexdigest() != md5:
            if retries:
                # try again
                log.debug("MD5 sums mismatch for download: %s (%s != %s), "
                          "trying again" % (url, h.hexdigest(), md5))
                return download(url, dst_path, session=session, md5=md5,
                                urlstxt=urlstxt, retries=retries - 1)
            raise RuntimeError("MD5 sums mismatch for download: %s (%s != %s)"
                               % (url, h.hexdigest(), md5))

        try:
            exp_backoff_fn(os.rename, pp, dst_path)
        except OSError as e:
            raise RuntimeError("Could not rename %r to %r: %r" %
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
