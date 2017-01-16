# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function, unicode_literals

import bz2
from conda import CondaError
from contextlib import closing
from functools import wraps
import hashlib
import json
from logging import DEBUG, getLogger
from mmap import ACCESS_READ, mmap
from os import makedirs
from os.path import getmtime, join
import re
from requests.exceptions import ConnectionError, HTTPError, SSLError
from requests.packages.urllib3.exceptions import InsecureRequestWarning
from textwrap import dedent
from time import time
import warnings

from .linked_data import linked_data
from .package_cache import PackageCache
from .._vendor.auxlib.entity import EntityEncoder
from .._vendor.auxlib.ish import dals
from .._vendor.auxlib.logz import stringify
from ..base.constants import (CONDA_HOMEPAGE_URL, MAX_CHANNEL_PRIORITY)
from ..base.context import context
from ..common.compat import ensure_text_type, ensure_unicode, iteritems, iterkeys, itervalues
from ..common.url import join_url
from ..connection import CondaSession
from ..exceptions import CondaHTTPError, CondaRuntimeError
from ..gateways.disk.read import read_index_json
from ..gateways.disk.update import touch
from ..models.channel import Channel, prioritize_channels
from ..models.dist import Dist
from ..models.index_record import EMPTY_LINK, IndexRecord

try:
    from cytoolz.itertoolz import take
except ImportError:
    from .._vendor.toolz.itertoolz import take


log = getLogger(__name__)
dotlog = getLogger('dotupdate')
stdoutlog = getLogger('stdoutlog')
stderrlog = getLogger('stderrlog')

fail_unknown_host = False

REPODATA_HEADER_RE = b'"(_etag|_mod|_cache_control)":[ ]?"(.*)"'

def supplement_index_with_prefix(index, prefix, channels):
    # type: (Dict[Dist, IndexRecord], str, Set[canonical_channel]) -> None  # NOQA
    # supplement index with information from prefix/conda-meta
    assert prefix
    maxp = len(channels) + 1
    for dist, info in iteritems(linked_data(prefix)):
        if dist in index:
            # The downloaded repodata takes priority, so we do not overwrite.
            # We do, however, copy the link information so that the solver
            # knows this package is installed.
            old_record = index[dist]
            link = info.get('link') or EMPTY_LINK
            index[dist] = IndexRecord.from_objects(old_record, link=link)
        else:
            # If the package is not in the repodata, use the local data. If
            # the 'depends' field is not present, we need to set it; older
            # installations are likely to have this.
            depends = info.get('depends') or ()
            # If the channel is known but the package is not in the index, it
            # is because 1) the channel is unavailable offline, or 2) it no
            # longer contains this package. Either way, we should prefer any
            # other version of the package to this one. On the other hand, if
            # it is in a channel we don't know about, assign it a value just
            # above the priority of all known channels.
            priority = MAX_CHANNEL_PRIORITY if dist.channel in channels else maxp
            index[dist] = IndexRecord.from_objects(info, depends=depends,
                                                   priority=priority)


def supplement_index_with_cache(index, channels):
    # type: (Dict[Dist, IndexRecord], Set[canonical_channel]) -> None  # NOQA
    # supplement index with packages from the cache
    maxp = len(channels) + 1
    for pc_entry in PackageCache.get_all_extracted_entries():
        dist = pc_entry.dist
        if dist in index:
            # The downloaded repodata takes priority
            continue
        pkg_dir = pc_entry.extracted_package_dir
        meta = read_index_json(pkg_dir)
        # See the discussion above about priority assignments.
        priority = MAX_CHANNEL_PRIORITY if dist.channel in channels else maxp
        rec = IndexRecord.from_objects(meta,
                                       fn=dist.to_filename(),
                                       schannel=dist.channel,
                                       priority=priority,
                                       url=dist.to_url())
        index[dist] = rec


def get_index(channel_urls=(), prepend=True, platform=None,
              use_local=False, use_cache=False, unknown=None, prefix=None):
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
    if context.offline and unknown is None:
        unknown = True

    channel_priority_map = prioritize_channels(channel_urls, platform=platform)
    index = fetch_index(channel_priority_map, use_cache=use_cache)

    if prefix or unknown:
        known_channels = {chnl for chnl, _ in itervalues(channel_priority_map)}
    if prefix:
        supplement_index_with_prefix(index, prefix, known_channels)
    if unknown:
        supplement_index_with_cache(index, known_channels)
    if context.add_pip_as_python_dependency:
        add_pip_dependency(index)
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


def read_mod_and_etag(path):
    with open(path, 'rb') as f:
        try:
            with closing(mmap(f.fileno(), 0, access=ACCESS_READ)) as m:
                match_objects = take(3, re.finditer(REPODATA_HEADER_RE, m))
                result = dict(map(ensure_unicode, mo.groups()) for mo in match_objects)
                return result
        except ValueError:
            # ValueError: cannot mmap an empty file
            return {}


def get_cache_control_max_age(cache_control_value):
    max_age = re.search(r"max-age=(\d+)", cache_control_value)
    return int(max_age.groups()[0]) if max_age else 0


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


def read_local_repodata(cache_path):
    with open(cache_path) as f:
        try:
            local_repodata = json.load(f)
        except ValueError as e:
            # ValueError: Expecting object: line 11750 column 6 (char 303397)
            log.debug("Error for cache path: '%s'\n%r", cache_path, e)
            message = dals("""
            An error occurred when loading cached repodata.  Executing
            `conda clean --index-cache` will remove cached repodata files
            so they can be downloaded again.
            """)
            raise CondaError(message)
        else:
            return local_repodata


@dotlog_on_return("fetching repodata:")
def fetch_repodata(url, cache_dir=None, use_cache=False, session=None):
    cache_path = join(cache_dir or create_cache_dir(), cache_fn_url(url))

    try:
        mtime = getmtime(cache_path)
    except (IOError, OSError):
        log.debug("No local cache found for %s at %s", url, cache_path)
        if use_cache:
            return {'packages': {}}
        else:
            mod_etag_headers = {}
    else:
        mod_etag_headers = read_mod_and_etag(cache_path)

        if context.local_repodata_ttl > 1:
            max_age = context.local_repodata_ttl
        elif context.local_repodata_ttl == 1:
            max_age = get_cache_control_max_age(mod_etag_headers.get('_cache_control', ''))
        else:
            max_age = 0

        timeout = mtime + max_age - time()
        if (timeout > 0 or context.offline) and not url.startswith('file://'):
            log.debug("Using cached repodata for %s at %s. Timeout in %d sec",
                      url, cache_path, timeout)
            return read_local_repodata(cache_path)

        log.debug("Locally invalidating cached repodata for %s at %s", url, cache_path)

    try:
        assert url is not None, url
        fetched_repodata = fetch_repodata_remote_request(session, url,
                                                         mod_etag_headers.get('_etag'),
                                                         mod_etag_headers.get('_mod'))
    except Response304ContentUnchanged:
        log.debug("304 NOT MODIFIED for '%s'. Updating mtime and loading from disk", url)
        touch(cache_path)
        return read_local_repodata(cache_path)

    with open(cache_path, 'w') as fo:
        json.dump(fetched_repodata, fo, indent=2, sort_keys=True, cls=EntityEncoder)

    return fetched_repodata or None


def _collect_repodatas_serial(use_cache, urls):
    # type: (bool, List[str]) -> List[Sequence[str, Option[Dict[Dist, IndexRecord]]]]
    session = CondaSession()
    repodatas = [(url, fetch_repodata(url, use_cache=use_cache, session=session))
                 for url in urls]
    return repodatas


def _collect_repodatas_concurrent(executor, use_cache, urls):
    futures = tuple(executor.submit(fetch_repodata, url, use_cache=use_cache,
                                    session=CondaSession()) for url in urls)
    repodatas = [(u, f.result()) for u, f in zip(urls, futures)]
    return repodatas


def _collect_repodatas(use_cache, urls):
    # TODO: there HAS to be a way to clean up this logic
    if context.concurrent:
        try:
            import concurrent.futures
            executor = concurrent.futures.ThreadPoolExecutor(10)
        except (ImportError, RuntimeError) as e:
            log.debug(repr(e))
            # concurrent.futures is only available in Python >= 3.2 or if futures is installed
            # RuntimeError is thrown if number of threads are limited by OS
            repodatas = _collect_repodatas_serial(use_cache, urls)
        else:
            try:
                repodatas = _collect_repodatas_concurrent(executor, use_cache, urls)
            except RuntimeError as e:
                # Cannot start new thread, then give up parallel execution
                log.debug(repr(e))
                repodatas = _collect_repodatas_serial(use_cache, urls)
            finally:
                executor.shutdown(wait=True)
    else:
        repodatas = _collect_repodatas_serial(use_cache, urls)

    return repodatas


def fetch_index(channel_urls, use_cache=False, index=None):
    # type: (prioritize_channels(), bool, bool, Dict[Dist, IndexRecord]) -> Dict[Dist, IndexRecord]
    log.debug('channel_urls=' + repr(channel_urls))
    if not context.json:
        stdoutlog.info("Fetching package metadata ...")

    urls = tuple(iterkeys(channel_urls))
    repodatas = _collect_repodatas(use_cache, urls)
    # type: List[Sequence[str, Option[Dict[Dist, IndexRecord]]]]
    #   this is sorta a lie; actually more primitve types

    def make_index(repodatas):
        result = dict()

        for channel_url, repodata in repodatas:
            if not repodata or not repodata.get('packages', {}):
                continue
            canonical_name, priority = channel_urls[channel_url]
            channel = Channel(channel_url)
            repodata_info = repodata.get('info', {})
            arch = repodata_info.get('arch')
            platform = repodata_info.get('platform')
            for fn, info in iteritems(repodata['packages']):
                rec = IndexRecord.from_objects(info,
                                               fn=fn,
                                               arch=arch,
                                               platform=platform,
                                               schannel=canonical_name,
                                               channel=channel_url,
                                               priority=priority,
                                               url=join_url(channel_url, fn),
                                               auth=channel.auth)
                result[Dist(rec)] = rec
        return result

    index = make_index(repodatas)

    if not context.json:
        stdoutlog.info('\n')
    return index


def cache_fn_url(url):
    # url must be right-padded with '/' to not invalidate any existing caches
    if not url.endswith('/'):
        url += '/'
    # subdir = url.rsplit('/', 1)[-1]
    # assert subdir in PLATFORM_DIRECTORIES or context.subdir != context._subdir, subdir
    md5 = hashlib.md5(url.encode('utf-8')).hexdigest()
    return '%s.json' % (md5[:8],)


def add_http_value_to_dict(resp, http_key, d, dict_key):
    value = resp.headers.get(http_key)
    if value:
        d[dict_key] = value


def add_pip_dependency(index):
    # TODO: discuss with @mcg1969 and document
    for dist, info in iteritems(index):
        if info['name'] == 'python' and info['version'].startswith(('2.', '3.')):
            index[dist] = IndexRecord.from_objects(info, depends=info['depends'] + ('pip',))


def create_cache_dir():
    cache_dir = join(context.pkgs_dirs[0], 'cache')
    try:
        makedirs(cache_dir)
    except OSError:
        pass
    return cache_dir


def dist_str_in_index(index, dist_str):
    return Dist(dist_str) in index
