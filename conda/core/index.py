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

from conda._vendor.auxlib.collection import first

from conda.exceptions import PackageNotFoundError

from .linked_data import linked_data
from .package_cache import PackageCache
from .. import CondaError
from .._vendor.auxlib.decorators import memoizedproperty, memoize
from .._vendor.auxlib.entity import EntityEncoder
from .._vendor.auxlib.ish import dals
from .._vendor.boltons.setutils import IndexedSet
from ..base.constants import (MAX_CHANNEL_PRIORITY, CONDA_TARBALL_EXTENSION, UNKNOWN_CHANNEL)
from ..base.context import context
from ..common.compat import ensure_unicode, iteritems, iterkeys, itervalues
from ..common.url import join_url
from ..connection import CondaSession
from ..gateways.disk.read import read_index_json
from ..gateways.disk.update import touch
from ..gateways.download import Response304ContentUnchanged, fetch_repodata_remote_request
from ..models.channel import Channel, prioritize_channels, MultiChannel
from ..models.dist import Dist
from ..models.index_record import EMPTY_LINK, IndexRecord
from ..resolve import MatchSpec

try:
    from cytoolz.itertoolz import concat, take
except ImportError:
    from .._vendor.toolz.itertoolz import concat, take


log = getLogger(__name__)
dotlog = getLogger('dotupdate')
stdoutlog = getLogger('stdoutlog')

fail_unknown_host = False


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
    # type: (Dict[Dist, IndexRecord], Set[canonical_channel]) -> None
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


def add_pip_dependency(index):
    # TODO: discuss with @mcg1969 and document
    for dist, info in iteritems(index):
        if info['name'] == 'python' and info['version'].startswith(('2.', '3.')):
            index[dist] = IndexRecord.from_objects(info, depends=info['depends'] + ('pip',))


def get_index_new(channel_urls=None, subdirs=None, prefix=None):
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
    if use_local:
        channel_urls = ['local'] + list(channel_urls)
    if prepend:
        channel_urls += context.channels

    return Index(channel_urls, context.subdirs, prefix)


def get_index_old(channel_urls=(), prepend=True, platform=None,
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
    # ('https://conda.anaconda.org/conda-forge/osx-64/', ('conda-forge', 1))

    # for url in channel_priority_map:
    #     if url not in Index._repodata_cache:
    #         # repodata = fetch_repodata(url) or {}
    #         # packages = repodata.get('packages', {})
    #         # Index._repodata_cache[url] = {Dist(join_url(url, fn)): info for fn, info in iteritems(packages)}
    #         Index._repodata_cache[url] = fetch_repodata(url) or {}

    index = fetch_index(channel_priority_map, use_cache=use_cache)

    if prefix or unknown:
        # this must always be True, otherwsise we'd get errors below
        known_channels = {chnl for chnl, _ in itervalues(channel_priority_map)}

    if prefix:
        supplement_index_with_prefix(index, prefix, known_channels)
    if unknown:
        supplement_index_with_cache(index, known_channels)
    if context.track_features:
        supplement_index_with_features(index)
    if context.add_pip_as_python_dependency:
        add_pip_dependency(index)
    return index


def dist_str_in_index(index, dist_str):
    return Dist(dist_str) in index


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
    _repodata_cache = {}
    _conda_session = CondaSession()

    def __init__(self, channels=(), subdirs=(), prefix=None):
        if channels:
            self._channels = channels
            self.subdirs = subdirs or context.subdirs
            self.prefix = prefix
            self._all_dists = None
        else:
            assert False
            self._index = index

    @memoizedproperty
    def channels(self):
        return IndexedSet(Channel(c) for c in self._channels)

    @memoizedproperty
    def channel_urls(self):
        return tuple(concat(c.urls(with_credentials=True, subdirs=self.subdirs)
                            for c in self.channels))

    def __getitem__(self, dist):
        return self._get_record(dist)
        # return self._index[dist]

    def __setitem__(self, key, value):
        raise NotImplementedError()

    def __delitem__(self, key):
        raise NotImplementedError()

    def get(self, dist, default=None):
        try:
            return self[dist]
        except PackageNotFoundError:
            return default

    def __contains__(self, dist):
        # return dist in self._index
        return dist in self._load_all_dists()

    def __iter__(self):
        # return iter(self._index)
        return iter(self._load_all_dists())

    def keys(self):
        return self.__iter__()

    def iteritems(self):
        # return iteritems(self._index)
        for dist in self:
            yield dist, self._get_record(dist)

    def items(self):
        return self.iteritems()

    def copy(self):
        raise NotImplementedError()

    def setdefault(self, key, default_value):
        raise NotImplementedError()

    def update(self, E=None, **F):
        raise NotImplementedError()

    def get_records_for_package_name(self, package_name):
        for url in self.channel_urls:
            repodata = self._get_repodata(url)
        raise NotImplementedError()

    def _load_all_dists(self):
        if self._all_dists is not None:
            return self._all_dists

        sources = []
        for channel_url in self.channel_urls:
            sources.append(self._get_repodata_dists(self._get_repodata(channel_url)))

        sources.extend(iter(PackageCache(pd)) for pd in context.pkgs_dirs)
        if self.prefix:
            sources.append(linked_data(self.prefix))
        _all_dists = self._all_dists = set(concat(sources))
        return _all_dists

    @staticmethod
    def _get_repodata_dists(repodata):
        repodata_dists = repodata.get('dists')
        if repodata_dists is None:
            # cache these dist objects on the repodata cache object
            channel_url = Channel(repodata['_url']).url(with_credentials=True)
            repodata_dists = repodata['dists'] = set(Dist(join_url(channel_url, fn)) for fn in repodata.get('packages', {}))
        return repodata_dists

    @memoize
    def _get_record(self, dist):

        # this whole block is all about figuring out what the channel_url is
        channel_url = None
        dist_url = dist.to_url()
        if dist.channel == UNKNOWN_CHANNEL:
            channel = Channel(UNKNOWN_CHANNEL)
        elif dist_url:
            channel = Channel(dist_url)
            assert channel.platform
            channel_url = channel.url(with_credentials=True)
            if channel_url.endswith(CONDA_TARBALL_EXTENSION):
                channel_url = channel_url.rsplit('/', 1)[0]
        else:
            # channel must be a multichannel
            channel = Channel(dist.channel)
            channel_urls = Channel(dist.channel).urls(with_credentials=True, subdirs=context.subdirs)
            assert channel_urls
            for url in channel_urls:
                repodata = self._get_repodata(url)
                repodata_dists = self._get_repodata_dists(repodata)
                repodata_dist = first(repodata_dists, key=lambda d: d.dist_name == dist.dist_name)
                if repodata_dist:
                    channel = Channel(url)
                    assert channel.platform
                    channel_url = channel.url(with_credentials=True)
                    if channel_url.endswith(CONDA_TARBALL_EXTENSION):
                        channel_url = channel_url.rsplit('/', 1)[0]

        fn = dist.to_filename()

        package_data = {
            "channel": channel_url,
            "fn": fn,
            "schannel": channel.canonical_name,
            "url": join_url(channel_url, fn) if channel_url else None,
        }

        # Step 1. look for repodata
        repodata_package = ()
        if channel_url:
            repodata = self._get_repodata(channel_url)
            repodata_package = repodata.get('packages', {}).get(fn)
            repodata_info = repodata.get('info', {})
            if repodata_package:
                package_data.update(repodata_package)
                package_data['arch'] = repodata_info.get('arch')
                package_data['platform'] = repodata_info.get('platform')

        # Step 2. look in package cache
        if repodata_package:
            # The downloaded repodata takes priority
            pass
        else:
            pc_entries = PackageCache.get_matching_entries(dist)
            if pc_entries:
                pkg_dir = pc_entries[0].extracted_package_dir
                index_json_record = read_index_json(pkg_dir)
                package_data.update(index_json_record.dump())

        # Step 3. look in prefix
        if self.prefix:
            linked_data_record = linked_data(self.prefix).get(dist)
            if linked_data_record:
                if repodata_package:
                    # The downloaded repodata takes priority, so we do not overwrite.
                    # We do, however, copy the link information so that the solver
                    # knows this package is installed.
                    link = linked_data_record.get('link') or EMPTY_LINK
                    package_data['link'] = link
                else:
                    # If the package is not in the repodata, use the local data in the prefix.
                    # Here we are preferring the prefix data over the package cache data.
                    package_data.update(linked_data_record.dump())

                    if 'depends' not in package_data:
                        # If the 'depends' field is not present, we need to set it; older
                        # installations are likely to have this.
                        package_data['depends'] = ()

        if len(package_data) <= 4:
            # <= 4 means no additional information was added
            raise PackageNotFoundError(dist.full_name, "")

        # Step 4. set priority
        if repodata_package and channel_url in self.channel_urls:
            package_data['priority'] = self.channel_urls.index(channel_url)
        else:
            # If the channel is known but the package is not in the index, it
            # is because 1) the channel is unavailable offline, or 2) it no
            # longer contains this package. Either way, we should prefer any
            # other version of the package to this one. On the other hand, if
            # it is in a channel we don't know about, assign it a value just
            # above the priority of all known channels.
            maxp = len(self.channels) + 1
            package_data['priority'] = MAX_CHANNEL_PRIORITY if channel_url in self.channel_urls else maxp

        # Step 5. add pip as dependency
        if context.add_pip_as_python_dependency:
            package_data['depends'] += ('pip',)

        return IndexRecord(**package_data)

    def _get_repodata(self, url):
        repodata = Index._repodata_cache.get(url)
        if repodata:
            return repodata
        repodata = Index._repodata_cache[url] = fetch_repodata(url) or {}
        return repodata




# ##########################################
# index fetching
# ##########################################

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


# ##########################################
# repodata fetching and on-disk caching
# ##########################################

REPODATA_HEADER_RE = b'"(_etag|_mod|_cache_control)":[ ]?"(.*)"'

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
def fetch_repodata(raw_url, cache_dir=None, use_cache=False, session=None):
    cache_path = join(cache_dir or create_cache_dir(), cache_fn_url(raw_url))
    session = session or Index._conda_session

    try:
        mtime = getmtime(cache_path)
    except (IOError, OSError):
        log.debug("No local cache found for %s at %s", raw_url, cache_path)
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
        if (timeout > 0 or context.offline) and not raw_url.startswith('file://'):
            log.debug("Using cached repodata for %s at %s. Timeout in %d sec",
                      raw_url, cache_path, timeout)
            return read_local_repodata(cache_path)

        log.debug("Locally invalidating cached repodata for %s at %s", raw_url, cache_path)

    try:
        assert raw_url is not None, raw_url
        fetched_repodata = fetch_repodata_remote_request(session, raw_url,
                                                         mod_etag_headers.get('_etag'),
                                                         mod_etag_headers.get('_mod'))
    except Response304ContentUnchanged:
        log.debug("304 NOT MODIFIED for '%s'. Updating mtime and loading from disk", raw_url)
        touch(cache_path)
        return read_local_repodata(cache_path)

    with open(cache_path, 'w') as fo:
        json.dump(fetched_repodata, fo, indent=2, sort_keys=True, cls=EntityEncoder)

    return fetched_repodata or None


def cache_fn_url(url):
    # url must be right-padded with '/' to not invalidate any existing caches
    if not url.endswith('/'):
        url += '/'
    # subdir = url.rsplit('/', 1)[-1]
    # assert subdir in PLATFORM_DIRECTORIES or context.subdir != context._subdir, subdir
    md5 = hashlib.md5(url.encode('utf-8')).hexdigest()
    return '%s.json' % (md5[:8],)


def create_cache_dir():
    cache_dir = join(context.pkgs_dirs[0], 'cache')
    try:
        makedirs(cache_dir)
    except OSError:
        pass
    return cache_dir


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
