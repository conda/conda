# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function, unicode_literals

import bz2
import hashlib
import json
import requests
import warnings
from conda.base.constants import DEFAULTS
from conda.models.dist import Dist
from functools import wraps
from logging import DEBUG, getLogger
from os.path import dirname, join
from requests.packages.urllib3.exceptions import InsecureRequestWarning

from .linked_data import linked_data
from .package_cache import package_cache

from .._vendor.auxlib.entity import EntityEncoder
from .._vendor.auxlib.logz import stringify
from ..base.context import context
from ..common.compat import iteritems, itervalues
from ..common.url import url_to_path
from ..connection import CondaSession, handle_proxy_407
from ..exceptions import CondaHTTPError, CondaRuntimeError
from ..fetch import create_cache_dir
from ..lock import FileLock
from ..models.channel import Channel, offline_keep, prioritize_channels
from ..models.record import EMPTY_LINK, Record

log = getLogger(__name__)
dotlog = getLogger('dotupdate')
stdoutlog = getLogger('stdoutlog')
stderrlog = getLogger('stderrlog')

fail_unknown_host = False


def get_index(channel_urls=(), prepend=True, platform=None, use_local=False, use_cache=False,
              unknown=False, prefix=False):
    """
    Return the index of packages available on the channels

    If prepend=False, only the channels passed in as arguments are used.
    If platform=None, then the current platform is used.
    If prefix is supplied, then the packages installed in that prefix are added.
    """
    if use_local:
        channel_urls = ['local'] + list(channel_urls)
    if prepend:
        channel_urls += context.channels
    channel_urls = prioritize_channels(channel_urls)
    index = fetch_index(channel_urls, use_cache=use_cache, unknown=unknown)

    # supplement index with information from prefix/conda-meta
    if prefix:
        priorities = {c: p for c, p in itervalues(channel_urls)}
        maxp = max(itervalues(priorities)) + 1 if priorities else 1
        for dist, info in iteritems(linked_data(prefix)):
            fn = info['fn']
            schannel = info['schannel']
            prefix = '' if schannel == DEFAULTS else schannel + '::'
            priority = priorities.get(schannel, maxp)
            key = Dist.from_string(prefix + fn)
            if key in index:
                # Copy the link information so the resolver knows this is installed
                index[key] = index[key].copy()
                index[key]['link'] = info.get('link') or EMPTY_LINK
            else:
                # only if the package in not in the repodata, use local
                # conda-meta (with 'depends' defaulting to [])
                info.setdefault('depends', [])
                info['priority'] = priority
                index[key] = info

    return index


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
            json.dump(cache, fo, indent=2, sort_keys=True, cls=EntityEncoder)
    except IOError:
        pass

    return cache or None


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

    def make_index(repodatas):
        result = dict()
        for channel, repodata in repodatas:
            if repodata is None:
                continue
            url_s, priority = channel_urls[channel]
            channel = channel.rstrip('/')
            for fn, info in iteritems(repodata['packages']):
                key = url_s + '::' + fn if url_s != DEFAULTS else fn
                key = Dist.from_string(key)
                url = channel + '/' + fn
                info.update(dict(fn=fn, schannel=url_s, channel=channel, priority=priority,
                                 url=url))
                result[key] = Record(**info)
        return result

    index = make_index(repodatas)

    stdoutlog.info('\n')
    if unknown:
        add_unknown(index, channel_urls)
    if context.add_pip_as_python_dependency:
        add_pip_dependency(index)
    return index


def cache_fn_url(url):
    md5 = hashlib.md5(url.encode('utf-8')).hexdigest()
    return '%s.json' % (md5[:8],)


def add_http_value_to_dict(resp, http_key, d, dict_key):
    value = resp.headers.get(http_key)
    if value:
        d[dict_key] = value


def add_unknown(index, priorities):
    priorities = {p[0]: p[1] for p in itervalues(priorities)}
    maxp = max(itervalues(priorities)) + 1 if priorities else 1
    for dist, info in iteritems(package_cache()):
        # schannel, dname = dist2pair(dist)
        fname = dist.to_filename()
        # fkey = dist + '.tar.bz2'
        if dist in index or not info['dirs']:
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
        if schannel2 != dist.channel:
            continue
        priority = priorities.get(dist.channel, maxp)
        if 'link' in meta:
            del meta['link']
        meta.update({'fn': fname,
                     'url': url,
                     'channel': channel,
                     'schannel': dist.channel,
                     'priority': priority,
                     })
        meta.setdefault('depends', [])
        log.debug("adding cached pkg to index: %s" % dist)
        index[dist] = meta


def add_pip_dependency(index):
    for info in itervalues(index):
        if info['name'] == 'python' and info['version'].startswith(('2.', '3.')):
            info['depends'] = info['depends'] + ('pip',)
