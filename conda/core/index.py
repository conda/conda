# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function, unicode_literals

from contextlib import closing
from functools import wraps
import hashlib
from itertools import chain
import json
from logging import getLogger
from mmap import ACCESS_READ, mmap
from os import makedirs
from os.path import getmtime, join
import re
from time import time

from .linked_data import linked_data
from .package_cache import PackageCache
from .. import CondaError
from .._vendor.auxlib.entity import EntityEncoder
from .._vendor.auxlib.ish import dals
from ..base.constants import (MAX_CHANNEL_PRIORITY)
from ..base.context import context
from ..common.compat import ensure_unicode, iteritems, iterkeys, itervalues
from ..common.url import join_url
from ..connection import CondaSession
from ..gateways.disk.read import read_index_json
from ..gateways.disk.update import touch
from ..gateways.download import Response304ContentUnchanged, fetch_repodata_remote_request
from ..models.channel import Channel, prioritize_channels
from ..models.dist import Dist
from ..models.index_record import EMPTY_LINK, IndexRecord
from ..resolve import MatchSpec

try:
    from cytoolz.itertoolz import take
except ImportError:
    from .._vendor.toolz.itertoolz import take


log = getLogger(__name__)
dotlog = getLogger('dotupdate')
stdoutlog = getLogger('stdoutlog')

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


def supplement_index_with_repodata(index, repodata, channel, priority):
    repodata_info = repodata.get('info', {})
    arch = repodata_info.get('arch')
    platform = repodata_info.get('platform')
    schannel = channel.canonical_name
    channel_url = channel.url()
    auth = channel.auth
    for fn, info in iteritems(repodata['packages']):
        rec = IndexRecord.from_objects(info,
                                       fn=fn,
                                       arch=arch,
                                       platform=platform,
                                       schannel=schannel,
                                       channel=channel_url,
                                       priority=priority,
                                       url=join_url(channel_url, fn),
                                       auth=auth)
        dist = Dist(rec)
        index[dist] = rec
        if 'with_features_depends' in info:
            base_deps = info.get('depends', ())
            base_feats = set(info.get('features', '').strip().split())
            for feat, deps in iteritems(info['with_features_depends']):
                feat = set(feat.strip().split())
                snames = {MatchSpec(s).name for s in deps}
                base2 = [s for s in base_deps if MatchSpec(s).name not in snames]
                feat2 = ' '.join(sorted(base_feats | feat))
                feat = ' '.join(sorted(feat))
                deps2 = base2 + deps
                dist = Dist.from_objects(dist, with_features_depends=feat)
                rec2 = IndexRecord.from_objects(rec, features=feat2, depends=deps2)
                index[dist] = rec2


def supplement_index_with_features(index, features=()):
    for feat in chain(context.track_features, features):
        fname = feat + '@'
        rec = IndexRecord(
            name=fname,
            version='0',
            build='0',
            schannel='defaults',
            track_features=feat,
            build_number=0,
            fn=fname)
        index[Dist(rec)] = rec


def get_index(channel_urls=None, subdirs=None, prefix=None):
    """

    Args:
        channel_urls (Option[Sequence[str]]): a list of channel urls
            if not given, context.channels is used
        subdirs: (Option[Sequence[str]]): a list of channel subdirs
            if not given, context.subdirs is used
        prefix: if supplied, the packages installed in the prefix are added


    """
    platform = subdirs[0] if subdirs else context.subdirs[0]
    channel_priority_map = prioritize_channels(
        channel_urls or context.channels,
        platform,
    )
    index = fetch_index(channel_priority_map)


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
    if context.track_features:
        supplement_index_with_features(index)
    if context.add_pip_as_python_dependency:
        add_pip_dependency(index)
    return Index(index)


class Index(object):
    """
    Three sources:
      1. repodata
      2. package cache
      3. prefix

    Keep a copy of repodata records exactly as it's downloaded.  Don't add a bunch of stuff to it.
    Things added to repodata records on fetch -- mostly channel information.

    The resolve logic for like features, track_features, ms_depends, find_matches, could be moved here.

    """

    def __init__(self, index):
        # assertion = lambda d, r: isinstance(d, Dist) and isinstance(r, IndexRecord)
        # assert all(assertion(d, r) for d, r in iteritems(index))

        feature_records = {}
        for dist, info in iteritems(index):
            if dist.with_features_depends:
                continue

            for feature_name in chain(info.get('features', '').split(),
                                      info.get('track_features', '').split(),
                                      context.track_features or ()):
                feature_dist = Dist(feature_name + '@')
                if feature_dist in index:
                    continue
                feature_records[feature_dist] = self.make_feature_record(feature_name, feature_dist)

            for feature_name in iterkeys(info.get('with_features_depends', {})):
                what_is_this_dist_for = Dist('%s[%s]' % (dist, feature_name))
                feature_records[what_is_this_dist_for] = info

                feature_dist = Dist(feature_name + '@')
                self.make_feature_record(feature_name, feature_dist)
                feature_records[feature_dist] = self.make_feature_record(feature_name, feature_dist)

        index.update(feature_records)
        self._index = index

    @staticmethod
    def make_feature_record(feature_name, feature_dist):
        info = {
            'name': feature_dist.dist_name,
            'channel': '@',
            'priority': 0,
            'version': '0',
            'build_number': 0,
            'fn': feature_dist.to_filename(),
            'build': '0',
            'depends': [],
            'track_features': feature_name,
        }
        return IndexRecord(**info)

    def __getitem__(self, dist):
        return self._index[dist]

    def __setitem__(self, key, value):
        raise NotImplementedError()

    def __delitem__(self, key):
        raise NotImplementedError()

    def get(self, dist, default=None):
        return self._index.get(dist, default)

    def __contains__(self, dist):
        # number 1 most common
        return dist in self._index

    def __iter__(self):
        return iter(self._index)

    def iteritems(self):
        return iteritems(self._index)

    def items(self):
        return self.iteritems()

    def copy(self):
        return self

    def setdefault(self, key, default_value):
        raise NotImplementedError()

    def update(self, E=None, **F):
        raise NotImplementedError()


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

    index = dict()
    for channel_url, repodata in repodatas:
        if repodata and repodata.get('packages'):
            _, priority = channel_urls[channel_url]
            channel = Channel(channel_url)
            supplement_index_with_repodata(index, repodata, channel, priority)

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
