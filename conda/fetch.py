# (c) 2012-2015 Continuum Analytics, Inc. / http://continuum.io
# All Rights Reserved
#
# conda is distributed under the terms of the BSD 3-clause license.
# Consult LICENSE.txt or http://opensource.org/licenses/BSD-3-Clause.

from __future__ import print_function, division, absolute_import

import bz2
import hashlib
import json
import os
import sys
import warnings
from logging import getLogger
from os.path import basename, isdir, join

import requests

from conda import config
from conda.common.compat import itervalues
from conda.common.connection import CondaSession
from conda.common.download import (add_http_value_to_dict, dotlog_on_return, handle_proxy_407,
                                   download)
from conda.common.utils import memoized

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
    md5 = hashlib.md5(url.encode('utf-8')).hexdigest()
    return '%s.json' % (md5[:8],)


@dotlog_on_return("fetching repodata:")
def fetch_repodata(url, cache_dir=None, use_cache=False, session=None):
    if not config.ssl_verify:
        try:
            from requests.packages.urllib3.connectionpool import InsecureRequestWarning
        except ImportError:
            pass
        else:
            warnings.simplefilter('ignore', InsecureRequestWarning)

    session = session or CondaSession(ssl_verify=config.ssl_verify,
                                      proxy_servers=config.get_proxy_servers())

    cache_path = join(cache_dir or create_cache_dir(), cache_fn_url(url))
    try:
        with open(cache_path) as f:
            cache = json.load(f)
    except (IOError, ValueError):
        cache = {'packages': {}}

    if use_cache:
        return cache

    headers = {}
    if "_etag" in cache:
        headers["If-None-Match"] = cache["_etag"]
    if "_mod" in cache:
        headers["If-Modified-Since"] = cache["_mod"]

    try:
        resp = session.get(url + 'repodata.json.bz2',
                           headers=headers, proxies=session.proxies)
        resp.close()
        resp.raise_for_status()
        if resp.status_code != 304:
            cache = json.loads(bz2.decompress(resp.content).decode('utf-8'))
            add_http_value_to_dict(resp, 'Etag', cache, '_etag')
            add_http_value_to_dict(resp, 'Last-Modified', cache, '_mod')

    except ValueError as e:
        raise RuntimeError("Invalid index file: %srepodata.json.bz2: %s" %
                           (config.remove_binstar_tokens(url), e))

    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 407: # Proxy Authentication Required
            handle_proxy_407(url, session)
            # Try again
            return fetch_repodata(url, cache_dir=cache_dir,
                                  use_cache=use_cache, session=session)

        if e.response.status_code == 404:
            if url.startswith(config.DEFAULT_CHANNEL_ALIAS):
                msg = ('Could not find anaconda.org user %s' %
                   config.remove_binstar_tokens(url).split(
                        config.DEFAULT_CHANNEL_ALIAS)[1].split('/')[0])
            else:
                if url.endswith('/noarch/'): # noarch directory might not exist
                    return None
                msg = 'Could not find URL: %s' % config.remove_binstar_tokens(url)
        elif e.response.status_code == 403 and url.endswith('/noarch/'):
            return None

        elif (e.response.status_code == 401 and config.rc.get('channel_alias',
                        config.DEFAULT_CHANNEL_ALIAS) in url):
            # Note, this will not trigger if the binstar configured url does
            # not match the conda configured one.
            msg = ("Warning: you may need to login to anaconda.org again with "
                "'anaconda login' to access private packages(%s, %s)" %
                (config.hide_binstar_tokens(url), e))
            stderrlog.info(msg)
            return fetch_repodata(config.remove_binstar_tokens(url),
                                  cache_dir=cache_dir,
                                  use_cache=use_cache, session=session)

        else:
            msg = "HTTPError: %s: %s\n" % (e, config.remove_binstar_tokens(url))

        log.debug(msg)
        raise RuntimeError(msg)

    except requests.exceptions.SSLError as e:
        msg = "SSL Error: %s\n" % e
        stderrlog.info("SSL verification error: %s\n" % e)
        log.debug(msg)

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

        msg = "Connection error: %s: %s\n" % (e, config.remove_binstar_tokens(url))
        stderrlog.info('Could not connect to %s\n' % config.remove_binstar_tokens(url))
        log.debug(msg)
        if fail_unknown_host:
            raise RuntimeError(msg)

    cache['_url'] = config.remove_binstar_tokens(url)
    try:
        with open(cache_path, 'w') as fo:
            json.dump(cache, fo, indent=2, sort_keys=True)
    except IOError:
        pass

    return cache or None


def add_unknown(index):
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
                meta['depends'] = []
            log.debug("adding cached pkg to index: %s" % fn)
            index[fn] = meta

def add_pip_dependency(index):
    for info in itervalues(index):
        if (info['name'] == 'python' and
                    info['version'].startswith(('2.', '3.'))):
            info.setdefault('depends', []).append('pip')

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

    try:
        import concurrent.futures
        from collections import OrderedDict

        repodatas = []
        with concurrent.futures.ThreadPoolExecutor(10) as executor:
            future_to_url = OrderedDict([(executor.submit(
                            fetch_repodata, url, use_cache=use_cache,
                            session=session), url)
                                         for url in reversed(channel_urls)])
            for future in future_to_url:
                url = future_to_url[future]
                repodatas.append((url, future.result()))
    except ImportError:
        # concurrent.futures is only available in Python 3
        repodatas = map(lambda url: (url, fetch_repodata(url,
                                     use_cache=use_cache, session=session)),
                        reversed(channel_urls))

    for url, repodata in repodatas:
        if repodata is None:
            continue
        new_index = repodata['packages']
        for info in itervalues(new_index):
            info['channel'] = url
        index.update(new_index)

    stdoutlog.info('\n')
    if unknown:
        add_unknown(index)
    if config.add_pip_as_python_dependency:
        add_pip_dependency(index)
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

    download(url, path, session=session, md5=info['md5'], urlstxt=True,
             ssl_verify=config.ssl_verify, proxy_servers=config.get_proxy_servers())
    if info.get('sig'):
        from conda.signature import verify, SignatureError

        fn2 = fn + '.sig'
        url = (info['channel'] if info['sig'] == '.' else
               info['sig'].rstrip('/') + '/') + fn2
        log.debug("signature url=%r" % url)
        download(url, join(dst_dir, fn2), session=session, ssl_verify=config.ssl_verify,
                 proxy_servers=config.get_proxy_servers())
        try:
            if verify(path):
                return
        except SignatureError as e:
            sys.exit(str(e))
        sys.exit("Error: Signature for '%s' is invalid." % (basename(path)))
