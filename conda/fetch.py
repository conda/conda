# (c) 2012-2014 Continuum Analytics, Inc. / http://continuum.io
# All Rights Reserved
#
# conda is distributed under the terms of the BSD 3-clause license.
# Consult LICENSE.txt or http://opensource.org/licenses/BSD-3-Clause.

from __future__ import print_function, division, absolute_import

import os
import bz2
import json
import shutil
import hashlib
import tempfile
from logging import getLogger
from os.path import basename, isdir, join
import sys
import getpass
# from multiprocessing.pool import ThreadPool

from conda import config
from conda.utils import memoized
from conda.connection import CondaSession, unparse_url
from conda.compat import itervalues, get_http_value, input
from conda.lock import Locked

import requests

log = getLogger(__name__)
dotlog = getLogger('dotupdate')
stdoutlog = getLogger('stdoutlog')
stderrlog = getLogger('stderrlog')

fail_unknown_host = False


def create_cache_dir():
    cache_dir = join(config.pkgs_dirs[0], 'cache')
    try:
        os.makedirs(cache_dir)
    except OSError:
        pass
    return cache_dir


def cache_fn_url(url):
    return '%s.json' % hashlib.md5(url.encode('utf-8')).hexdigest()


def add_http_value_to_dict(u, http_key, d, dict_key):
    value = get_http_value(u, http_key)
    if value:
        d[dict_key] = value


def fetch_repodata(url, cache_dir=None, use_cache=False, session=None):
    dotlog.debug("fetching repodata: %s ..." % url)

    session = session or CondaSession()

    cache_path = join(cache_dir or create_cache_dir(), cache_fn_url(url))
    try:
        cache = json.load(open(cache_path))
    except (IOError, ValueError):
        cache = {'packages': {}}

    if use_cache:
        return cache

    headers = {}
    if "_tag" in cache:
        headers["If-None-Match"] = cache["_etag"]
    if "_mod" in cache:
        headers["If-Modified-Since"] = cache["_mod"]

    try:
        resp = session.get(url + 'repodata.json.bz2',
                           headers=headers, proxies=session.proxies,
                           verify=config.ssl_verify)
        resp.raise_for_status()
        if resp.status_code != 304:
            cache = json.loads(bz2.decompress(resp.content).decode('utf-8'))

    except ValueError as e:
        raise RuntimeError("Invalid index file: %srepodata.json.bz2: %s" %
                           (url, e))

    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 407: # Proxy Authentication Required
            handle_proxy_407(url, session)
            # Try again
            return fetch_repodata(url, cache_dir=cache_dir,
                                  use_cache=use_cache, session=session)
        if e.response.status_code == 404:
            if url.startswith(config.DEFAULT_CHANNEL_ALIAS):
                msg = 'Could not find Binstar user %s' % url.split(config.DEFAULT_CHANNEL_ALIAS)[1].split('/')[0]
            else:
                msg = 'Could not find URL: %s' % url
        else:
            msg = "HTTPError: %s: %s\n" % (e, url)
        log.debug(msg)
        raise RuntimeError(msg)

    except requests.exceptions.ConnectionError as e:
        # requests isn't so nice here. For whatever reason, https gives this
        # error and http gives the above error. Also, there is no status_code
        # attribute here. We have to just check if it looks like 407.  See
        # https://github.com/kennethreitz/requests/issues/2061.
        if "407" in str(e): # Proxy Authentication Required
            handle_proxy_407(url, session)
            # Try again
            return fetch_repodata(url, cache_dir=cache_dir,
                                  use_cache=use_cache, session=session)

        msg = "Connection error: %s: %s\n" % (e, url)
        stderrlog.info('Could not connect to %s\n' % url)
        log.debug(msg)
        if fail_unknown_host:
            raise RuntimeError(msg)

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
    username, passwd = get_proxy_username_and_pass(scheme)
    session.proxies[scheme] = add_username_and_pass_to_url(
                           session.proxies[scheme], username, passwd)

def add_username_and_pass_to_url(url, username, passwd):
    urlparts = list(requests.packages.urllib3.util.url.parse_url(url))
    urlparts[1] = username + ':' + passwd
    return unparse_url(urlparts)

def get_proxy_username_and_pass(scheme):
    username = input("\n%s proxy username: " % scheme)
    passwd = getpass.getpass("Password:")
    return username, passwd

@memoized
def fetch_index(channel_urls, use_cache=False, unknown=False):
    log.debug('channel_urls=' + repr(channel_urls))
    # pool = ThreadPool(5)
    index = {}
    stdoutlog.info("Fetching package metadata: ")
    session = CondaSession()
    for url in reversed(channel_urls):
        if config.allowed_channels and url not in config.allowed_channels:
            sys.exit("""
Error: URL '%s' not in allowed channels.

Allowed channels are:
  - %s
""" % (url, '\n  - '.join(config.allowed_channels)))

    repodatas = map(lambda url: (url, fetch_repodata(url,
        use_cache=use_cache, session=session)), reversed(channel_urls))
    for url, repodata in repodatas:
        if repodata is None:
            continue
        new_index = repodata['packages']
        for info in itervalues(new_index):
            info['channel'] = url
        index.update(new_index)
    stdoutlog.info('\n')
    if unknown:
        for pkgs_dir in config.pkgs_dirs:
            if not isdir(pkgs_dir):
                continue
            for dn in os.listdir(pkgs_dir):
                fn = dn + '.tar.bz2'
                if fn in index:
                    continue
                try:
                    with open(join(pkgs_dir, dn, 'info', 'index.json')) as fi:
                        meta = json.load(fi)
                except IOError:
                    continue
                if 'depends' not in meta:
                    continue
                log.debug("adding cached pkg to index: %s" % fn)
                index[fn] = meta

    return index

def fetch_pkg(info, dst_dir=None, session=None):
    '''
    fetch a package given by `info` and store it into `dst_dir`
    '''
    if dst_dir is None:
        dst_dir = config.pkgs_dirs[0]

    session = session or CondaSession()

    fn = '%(name)s-%(version)s-%(build)s.tar.bz2' % info
    url = info['channel'] + fn
    log.debug("url=%r" % url)
    path = join(dst_dir, fn)

    download(url, path, session=session, md5=info['md5'], urlstxt=True)


def download(url, dst_path, session=None, md5=None, urlstxt=False):
    pp = dst_path + '.part'
    dst_dir = os.path.split(dst_path)[0]
    session = session or CondaSession()

    with Locked(dst_dir):
        try:
            resp = session.get(url, stream=True, proxies=session.proxies,
                               verify=config.ssl_verify)
            resp.raise_for_status()
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 407: # Proxy Authentication Required
                handle_proxy_407(url, session)
                # Try again
                return download(url, dst_path, session=session, md5=md5,
                                urlstxt=urlstxt)
            msg = "HTTPError: %s: %s\n" % (e, url)
            log.debug(msg)
            raise RuntimeError(msg)

        except requests.exceptions.ConnectionError as e:
            # requests isn't so nice here. For whatever reason, https gives this
            # error and http gives the above error. Also, there is no status_code
            # attribute here. We have to just check if it looks like 407.  See
            # https://github.com/kennethreitz/requests/issues/2061.
            if "407" in str(e): # Proxy Authentication Required
                handle_proxy_407(url, session)
                # Try again
                return download(url, dst_path, session=session, md5=md5,
                    urlstxt=urlstxt)
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

        n = 0
        if md5:
            h = hashlib.new('md5')
        try:
            with open(pp, 'wb') as fo:
                for chunk in resp.iter_content(2**14):
                    try:
                        fo.write(chunk)
                    except IOError:
                        raise RuntimeError("Failed to write to %r." % pp)
                    if md5:
                        h.update(chunk)
                    n += len(chunk)
                    if size:
                        getLogger('fetch.update').info(n)
        except IOError:
            raise RuntimeError("Could not open %r for writing.  "
                "Permissions problem or missing directory?" % pp)

        if size:
            getLogger('fetch.stop').info(None)

        if md5 and h.hexdigest() != md5:
            raise RuntimeError("MD5 sums mismatch for download: %s (%s != %s)"
                               % (url, h.hexdigest(), md5))

        try:
            os.rename(pp, dst_path)
        except OSError as e:
            raise RuntimeError("Could not rename %r to %r: %r" % (pp,
                dst_path, e))

        if urlstxt:
            try:
                with open(join(dst_dir, 'urls.txt'), 'a') as fa:
                    fa.write('%s\n' % url)
            except IOError:
                pass

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
                from conda.console import setup_handlers
                setup_handlers()
            self.tmp_dir = tempfile.mkdtemp()
            dst = join(self.tmp_dir, basename(self.url))
            download(self.url, dst)
            return dst

    def __exit__(self, exc_type, exc_value, traceback):
        if self.tmp_dir:
            shutil.rmtree(self.tmp_dir)
