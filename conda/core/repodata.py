# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function, unicode_literals

import bz2
from contextlib import closing
from genericpath import getmtime, isfile
import hashlib
import json
from logging import DEBUG, getLogger
from mmap import ACCESS_READ, mmap
from os import makedirs
from os.path import dirname, join, split as path_split
import re
from textwrap import dedent
from time import time
import warnings
from collections import OrderedDict

from .. import CondaError, iteritems
from .._vendor.auxlib.entity import EntityEncoder
from .._vendor.auxlib.ish import dals
from .._vendor.auxlib.logz import stringify
from ..base.constants import CONDA_HOMEPAGE_URL, UNKNOWN_CHANNEL
from ..base.context import context
from ..common.compat import (ensure_binary, ensure_text_type, ensure_unicode,
                             text_type, with_metaclass)
from ..common.url import join_url, maybe_unquote
from ..core.package_cache import PackageCache
from ..exceptions import CondaDependencyError, CondaHTTPError, CondaIndexError
from ..gateways.connection import (ConnectionError, HTTPError, InsecureRequestWarning,
                                   InvalidSchema, SSLError)
from ..gateways.connection.session import CondaSession
from ..gateways.disk.delete import rm_rf
from ..gateways.disk.update import touch
from ..models.channel import Channel
from ..models.dist import Dist
from ..models.index_record import IndexRecord, Priority

try:
    from cytoolz.itertoolz import concat, take
except ImportError:  # pragma: no cover
    from .._vendor.toolz.itertoolz import concat, take  # NOQA

try:
    import cPickle as pickle
except ImportError:  # pragma: no cover
    import pickle  # NOQA

__all__ = ('RepoData',)

log = getLogger(__name__)
stderrlog = getLogger('stderrlog')

REPODATA_PICKLE_VERSION = 3
REPODATA_HEADER_RE = b'"(_etag|_mod|_cache_control)":[ ]?"(.*)"'


class RepoDataType(type):
    """This (meta) class provides (ordered) dictionary-like access to Repodata."""

    def __init__(cls, name, bases, dict):
        cls._instances = OrderedDict()

    def __getitem__(cls, url):
        return cls._instances[url]

    def __iter__(cls):
        return iter(cls._instances)

    def __reversed__(cls):
        return reversed(cls._instances)

    def __len__(cls):
        return len(cls._instances)

@with_metaclass(RepoDataType)
class RepoData(object):
    """This object represents all the package metainfo of a single channel."""

    @staticmethod
    def enable(url, name, priority, cache_dir=None):
        RepoData._instances[url] = RepoData(url, name, priority, cache_dir)

    @staticmethod
    def get(url):
        return RepoData._instances.get(url)

    @staticmethod
    def clear():
        RepoData._instances.clear()

    @staticmethod
    def load_all(use_cache=False):
        try:
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor(10) as e:
                for rd in RepoData._instances.values():
                    e.submit(rd.load(use_cache=use_cache, session=CondaSession()))
        except (ImportError) as e:
            for rd in RepoData._instances.values():
                rd.load(use_cache=use_cache, session=CondaSession())

    def __init__(self, url, name, priority, cache_dir=None):
        """Create a RepoData object."""

        self.url = url
        self.name = name
        self.priority = priority
        self.cache_dir = cache_dir
        self._data = None

    def load(self, use_cache=False, session=None):
        """Syncs this object with an upstream RepoData object."""

        session = session if session else CondaSession()
        self._data = fetch_repodata(self.url, self.name, self.priority,
                                    cache_dir=self.cache_dir,
                                    use_cache=use_cache, session=session)

    def _persist(self, cache_dir=None):
        """Save data to local cache."""

        cache_path = join(cache_dir or self.cache_dir or create_cache_dir(),
                          cache_fn_url(self.url))
        write_pickled_repodata(cache_path, self._data)

    def query(self, query):
        """query information about a package"""
        raise NotImplemented

    def contains(self, package_ref):
        """Check whether the package is contained in this channel."""
        raise NotImplemented

    def validate(self, package_ref):
        """Check whether the package could be added to this channel."""
        raise NotImplemented

    def add(self, package_ref):
        """Add the given package-ref to this channel."""
        raise NotImplemented

    def remove(self, package_ref):
        """Remove the given package-ref from this channel."""
        raise NotImplemented

    @property
    def index(self):
        # WARNING: This method will soon be deprecated.
        return self._data


def read_mod_and_etag(path):
    with open(path, 'rb') as f:
        try:
            with closing(mmap(f.fileno(), 0, access=ACCESS_READ)) as m:
                match_objects = take(3, re.finditer(REPODATA_HEADER_RE, m))
                result = dict(map(ensure_unicode, mo.groups()) for mo in match_objects)
                return result
        except (BufferError, ValueError):
            # BufferError: cannot close exported pointers exist
            #   https://github.com/conda/conda/issues/4592
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
    except InvalidSchema as e:
        if 'SOCKS' in text_type(e):
            message = dals("""
            Requests has identified that your current working environment is configured
            to use a SOCKS proxy, but pysocks is not installed.  To proceed, remove your
            proxy configuration, run `conda install pysocks`, and then you can re-enable
            your proxy configuration.
            """)
            raise CondaDependencyError(message)
        else:
            raise

    except (ConnectionError, HTTPError, SSLError) as e:
        # status_code might not exist on SSLError
        status_code = getattr(e.response, 'status_code', None)
        if status_code == 404:
            if not url.endswith('/noarch'):
                return None
            else:
                if context.allow_non_channel_urls:
                    help_message = dedent("""
                    WARNING: The remote server could not find the noarch directory for the
                    requested channel with url: %s

                    It is possible you have given conda an invalid channel. Please double-check
                    your conda configuration using `conda config --show`.

                    If the requested url is in fact a valid conda channel, please request that the
                    channel administrator create `noarch/repodata.json` and associated
                    `noarch/repodata.json.bz2` files, even if `noarch/repodata.json` is empty.
                    $ mkdir noarch
                    $ echo '{}' > noarch/repodata.json
                    $ bzip2 -k noarch/repodata.json
                    """) % maybe_unquote(dirname(url))
                    stderrlog.warn(help_message)
                    return None
                else:
                    help_message = dals("""
                    The remote server could not find the noarch directory for the
                    requested channel with url: %s

                    As of conda 4.3, a valid channel must contain a `noarch/repodata.json` and
                    associated `noarch/repodata.json.bz2` file, even if `noarch/repodata.json` is
                    empty. please request that the channel administrator create
                    `noarch/repodata.json` and associated `noarch/repodata.json.bz2` files.
                    $ mkdir noarch
                    $ echo '{}' > noarch/repodata.json
                    $ bzip2 -k noarch/repodata.json

                    You will need to adjust your conda configuration to proceed.
                    Use `conda config --show` to view your configuration's current state.
                    Further configuration help can be found at <%s>.
                    """) % (maybe_unquote(dirname(url)),
                            join_url(CONDA_HOMEPAGE_URL, 'docs/config.html'))

        elif status_code == 403:
            if not url.endswith('/noarch'):
                return None
            else:
                if context.allow_non_channel_urls:
                    help_message = dedent("""
                    WARNING: The remote server could not find the noarch directory for the
                    requested channel with url: %s

                    It is possible you have given conda an invalid channel. Please double-check
                    your conda configuration using `conda config --show`.

                    If the requested url is in fact a valid conda channel, please request that the
                    channel administrator create `noarch/repodata.json` and associated
                    `noarch/repodata.json.bz2` files, even if `noarch/repodata.json` is empty.
                    $ mkdir noarch
                    $ echo '{}' > noarch/repodata.json
                    $ bzip2 -k noarch/repodata.json
                    """) % maybe_unquote(dirname(url))
                    stderrlog.warn(help_message)
                    return None
                else:
                    help_message = dals("""
                    The remote server could not find the noarch directory for the
                    requested channel with url: %s

                    As of conda 4.3, a valid channel must contain a `noarch/repodata.json` and
                    associated `noarch/repodata.json.bz2` file, even if `noarch/repodata.json` is
                    empty. please request that the channel administrator create
                    `noarch/repodata.json` and associated `noarch/repodata.json.bz2` files.
                    $ mkdir noarch
                    $ echo '{}' > noarch/repodata.json
                    $ bzip2 -k noarch/repodata.json

                    You will need to adjust your conda configuration to proceed.
                    Use `conda config --show` to view your configuration's current state.
                    Further configuration help can be found at <%s>.
                    """) % (maybe_unquote(dirname(url)),
                            join_url(CONDA_HOMEPAGE_URL, 'docs/config.html'))

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
               """) % (channel.token, join_url(CONDA_HOMEPAGE_URL, 'docs/config.html'))

            elif context.channel_alias.location in url:
                # Note, this will not trigger if the binstar configured url does
                # not match the conda configured one.
                help_message = dals("""
                The remote server has indicated you are using invalid credentials for this channel.

                If the remote site is anaconda.org or follows the Anaconda Server API, you
                will need to
                  (a) remove the invalid token from your system with `anaconda logout`, optionally
                      followed by collecting a new token with `anaconda login`, or
                  (b) provide conda with a valid token directly.

                Further configuration help can be found at <%s>.
               """) % join_url(CONDA_HOMEPAGE_URL, 'docs/config.html')

            else:
                help_message = dals("""
                The credentials you have provided for this URL are invalid.

                You will need to modify your conda configuration to proceed.
                Use `conda config --show` to view your configuration's current state.
                Further configuration help can be found at <%s>.
                """) % join_url(CONDA_HOMEPAGE_URL, 'docs/config.html')

        elif status_code is not None and 500 <= status_code < 600:
            help_message = dals("""
            An remote server error occurred when trying to retrieve this URL.

            A 500-type error (e.g. 500, 501, 502, 503, etc.) indicates the server failed to
            fulfill a valid request.  The problem may be spurious, and will resolve itself if you
            try your request again.  If the problem persists, consider notifying the maintainer
            of the remote server.
            """)

        else:
            help_message = dals("""
            An HTTP error occurred when trying to retrieve this URL.
            HTTP errors are often intermittent, and a simple retry will get you on your way.
            %s
            """) % maybe_unquote(repr(e))

        raise CondaHTTPError(help_message,
                             join_url(url, filename),
                             status_code,
                             getattr(e.response, 'reason', None),
                             getattr(e.response, 'elapsed', None),
                             e.response)

    except ValueError as e:
        raise CondaIndexError("Invalid index file: {0}: {1}".format(join_url(url, filename), e))


def write_pickled_repodata(cache_path, repodata):
    # Don't bother to pickle empty channels
    if not repodata.get('packages'):
        return
    try:
        with open(get_pickle_path(cache_path), 'wb') as f:
            pickle.dump(repodata, f)
    except Exception as e:
        import traceback
        log.debug("Failed to dump pickled repodata.\n%s", traceback.format_exc())


def read_pickled_repodata(cache_path, channel_url, schannel, priority, etag, mod_stamp):
    pickle_path = get_pickle_path(cache_path)
    # Don't trust pickled data if there is no accompanying json data
    if not isfile(pickle_path) or not isfile(cache_path):
        return None
    try:
        if isfile(pickle_path):
            log.debug("found pickle file %s", pickle_path)
        with open(pickle_path, 'rb') as f:
            repodata = pickle.load(f)
    except Exception as e:
        import traceback
        log.debug("Failed to load pickled repodata.\n%s", traceback.format_exc())
        rm_rf(pickle_path)
        return None

    def _check_pickled_valid():
        yield repodata.get('_url') == channel_url
        yield repodata.get('_schannel') == schannel
        yield repodata.get('_add_pip') == context.add_pip_as_python_dependency
        yield repodata.get('_mod') == mod_stamp
        yield repodata.get('_etag') == etag
        yield repodata.get('_pickle_version') == REPODATA_PICKLE_VERSION

    if not all(_check_pickled_valid()):
        return None

    if int(repodata['_priority']) != priority:
        log.debug("setting priority for %s to '%d'", repodata.get('_url'), priority)
        repodata['_priority']._priority = priority

    return repodata


def read_local_repodata(cache_path, channel_url, schannel, priority, etag, mod_stamp):
    local_repodata = read_pickled_repodata(cache_path, channel_url, schannel, priority,
                                           etag, mod_stamp)
    if local_repodata:
        return local_repodata
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
            process_repodata(local_repodata, channel_url, schannel, priority)
            write_pickled_repodata(cache_path, local_repodata)
            return local_repodata


def make_feature_record(feature_name):
    # necessary for the SAT solver to do the right thing with features
    pkg_name = feature_name + '@'
    return IndexRecord(
        name=pkg_name,
        version='0',
        build='0',
        channel=UNKNOWN_CHANNEL,
        subdir=context.subdir,
        md5="0123456789",
        track_features=feature_name,
        build_number=0,
        fn=pkg_name,
    )


def process_repodata(repodata, channel_url, schannel, priority):
    opackages = repodata.setdefault('packages', {})
    if not opackages:
        return repodata

    subdir = repodata.get('info', {}).get('subdir') or Channel(channel_url).subdir

    repodata['_add_pip'] = add_pip = context.add_pip_as_python_dependency
    repodata['_pickle_version'] = REPODATA_PICKLE_VERSION
    repodata['_priority'] = priority = Priority(priority)
    repodata['_schannel'] = schannel
    repodata['_subdir'] = subdir

    meta_in_common = {  # just need to make this once, then apply with .update()
        'arch': repodata.get('info', {}).get('arch'),
        'channel': channel_url,
        'platform': repodata.get('info', {}).get('platform'),
        'priority': priority,
        'schannel': schannel,
        'subdir': subdir,
    }
    packages = {}
    feature_names = set()
    for fn, info in iteritems(opackages):
        info['fn'] = fn
        info['url'] = join_url(channel_url, fn)
        if add_pip and info['name'] == 'python' and info['version'].startswith(('2.', '3.')):
            info['depends'].append('pip')
        info.update(meta_in_common)
        rec = IndexRecord(**info)
        packages[Dist(rec)] = rec
        if rec.features:
            feature_names.update(rec.features)
        if rec.track_features:
            feature_names.update(rec.track_features)

    for feature_name in feature_names:
        rec = make_feature_record(feature_name)
        packages[Dist(rec)] = rec

    repodata['packages'] = packages


def fetch_repodata(url, schannel, priority,
                   cache_dir=None, use_cache=False, session=None):
    cache_path = join(cache_dir or create_cache_dir(), cache_fn_url(url))

    try:
        mtime = getmtime(cache_path)
    except (IOError, OSError):
        log.debug("No local cache found for %s at %s", url, cache_path)
        if use_cache or (context.offline and not url.startswith('file://')):
            return {'packages': {}}
        else:
            mod_etag_headers = {}
    else:
        mod_etag_headers = read_mod_and_etag(cache_path)

        if use_cache:
            log.debug("Using cached repodata for %s at %s because use_cache=True",
                      url, cache_path)
            return read_local_repodata(cache_path, url, schannel, priority,
                                       mod_etag_headers.get('_etag'), mod_etag_headers.get('_mod'))

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
            return read_local_repodata(cache_path, url, schannel, priority,
                                       mod_etag_headers.get('_etag'), mod_etag_headers.get('_mod'))

        log.debug("Locally invalidating cached repodata for %s at %s", url, cache_path)

    try:
        assert url is not None, url
        repodata = fetch_repodata_remote_request(session, url,
                                                 mod_etag_headers.get('_etag'),
                                                 mod_etag_headers.get('_mod'))
    except Response304ContentUnchanged:
        log.debug("304 NOT MODIFIED for '%s'. Updating mtime and loading from disk", url)
        touch(cache_path)
        return read_local_repodata(cache_path, url, schannel, priority,
                                   mod_etag_headers.get('_etag'), mod_etag_headers.get('_mod'))
    if repodata is None:
        return None

    with open(cache_path, 'w') as fo:
        json.dump(repodata, fo, indent=2, sort_keys=True, cls=EntityEncoder)

    process_repodata(repodata, url, schannel, priority)
    write_pickled_repodata(cache_path, repodata)
    return repodata


def _collect_repodatas_concurrent_as_index(executor, use_cache, tasks):
    futures = (executor.submit(fetch_repodata, url, schan, pri,
                               use_cache=use_cache,
                               session=CondaSession())
               for url, schan, pri in tasks)
    results = (future.result() for future in futures)
    index = dict(concat(iteritems(result.get('packages', {})) for result in results if result))
    return index


def _collect_repodatas_serial_as_index(use_cache, tasks):
    session = CondaSession()
    results = (fetch_repodata(url, schan, pri, use_cache=use_cache, session=session)
               for url, schan, pri in tasks)
    index = dict(concat(iteritems(result.get('packages', {})) for result in results if result))
    return index


def collect_all_repodata_as_index(use_cache, tasks):
    index = executor = None
    if context.concurrent:
        try:
            from concurrent.futures import ThreadPoolExecutor
            executor = ThreadPoolExecutor(5)
            index = _collect_repodatas_concurrent_as_index(executor, use_cache, tasks)
        except (ImportError, RuntimeError) as e:
            # concurrent.futures is only available in Python >= 3.2 or if futures is installed
            # RuntimeError is thrown if number of threads are limited by OS
            log.debug(repr(e))
    if executor:
        executor.shutdown(wait=True)
    if index is None:
        index = _collect_repodatas_serial_as_index(use_cache, tasks)
    return index


def cache_fn_url(url):
    # url must be right-padded with '/' to not invalidate any existing caches
    if not url.endswith('/'):
        url += '/'
    md5 = hashlib.md5(ensure_binary(url)).hexdigest()
    return '%s.json' % (md5[:8],)


def get_pickle_path(cache_path):
    cache_dir, cache_base = path_split(cache_path)
    return join(cache_dir, cache_base.replace('.json', '.q'))


def add_http_value_to_dict(resp, http_key, d, dict_key):
    value = resp.headers.get(http_key)
    if value:
        d[dict_key] = value


def create_cache_dir():
    cache_dir = join(PackageCache.first_writable(context.pkgs_dirs).pkgs_dir, 'cache')
    try:
        makedirs(cache_dir)
    except OSError:
        pass
    return cache_dir
