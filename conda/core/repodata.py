# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function, unicode_literals

import bz2
from collections import defaultdict
from contextlib import closing
from genericpath import getmtime, isfile
import hashlib
import json
from logging import DEBUG, getLogger
from mmap import ACCESS_READ, mmap
from os import makedirs
from os.path import dirname, join, splitext
import re
from textwrap import dedent
from time import time
import warnings

from .. import CondaError, iteritems
from .._vendor.auxlib.ish import dals
from .._vendor.auxlib.logz import stringify
from ..base.constants import CONDA_HOMEPAGE_URL
from ..base.context import context
from ..common.compat import (ensure_binary, ensure_text_type, ensure_unicode, odict, text_type,
                             with_metaclass)
from ..common.url import join_url, maybe_unquote
from ..core.package_cache import PackageCache
from ..exceptions import CondaDependencyError, CondaHTTPError, CondaIndexError
from ..gateways.connection import (ConnectionError, HTTPError, InsecureRequestWarning,
                                   InvalidSchema, SSLError)
from ..gateways.connection.session import CondaSession
from ..gateways.disk.delete import rm_rf
from ..gateways.disk.update import touch
from ..models.channel import Channel, prioritize_channels
from ..models.dist import Dist
from ..models.index_record import IndexRecord, PackageRecord, Priority
from ..models.match_spec import MatchSpec

try:
    from cytoolz.itertoolz import concat, take
except ImportError:  # pragma: no cover
    from .._vendor.toolz.itertoolz import concat, take  # NOQA

try:
    import cPickle as pickle
except ImportError:  # pragma: no cover
    import pickle  # NOQA

log = getLogger(__name__)
stderrlog = getLogger('conda.stderrlog')

REPODATA_PICKLE_VERSION = 5
REPODATA_HEADER_RE = b'"(_etag|_mod|_cache_control)":[ ]?"(.*?[^\\\\])"[,\}\s]'


# class RepoDataType(type):
#     """This (meta) class provides (ordered) dictionary-like access to Repodata."""
#
#     def __init__(cls, name, bases, dict):
#         cls._instances = OrderedDict()
#
#     def __getitem__(cls, url):
#         return cls._instances[url]
#
#     def __iter__(cls):
#         return iter(cls._instances)
#
#     def __reversed__(cls):
#         return reversed(cls._instances)
#
#     def __len__(cls):
#         return len(cls._instances)
#
# @with_metaclass(RepoDataType)
# class RepoData(object):
#     """This object represents all the package metainfo of a single channel."""
#
#     @staticmethod
#     def enable(url, name, priority, cache_dir=None):
#         RepoData._instances[url] = RepoData(url, name, priority, cache_dir)
#
#     @staticmethod
#     def get(url):
#         return RepoData._instances.get(url)
#
#     @staticmethod
#     def clear():
#         RepoData._instances.clear()
#
#     @staticmethod
#     def load_all(use_cache=False):
#         try:
#             import concurrent.futures
#             with concurrent.futures.ThreadPoolExecutor(10) as e:
#                 for rd in RepoData._instances.values():
#                     e.submit(rd.load(use_cache=use_cache, session=CondaSession()))
#         except (ImportError) as e:
#             for rd in RepoData._instances.values():
#                 rd.load(use_cache=use_cache, session=CondaSession())
#
#     def __init__(self, url, name, priority, cache_dir=None):
#         """Create a RepoData object."""
#
#         self.url = url
#         self.name = name
#         self.priority = priority
#         self.cache_dir = cache_dir
#         self._data = None
#
#     def load(self, use_cache=False, session=None):
#         """Syncs this object with an upstream RepoData object."""
#
#         session = session if session else CondaSession()
#         self._data = fetch_repodata(self.url, self.name, self.priority,
#                                     cache_dir=self.cache_dir,
#                                     use_cache=use_cache, session=session)
#
#     def _persist(self, cache_dir=None):
#         """Save data to local cache."""
#
#         cache_path = join(cache_dir or self.cache_dir or create_cache_dir(),
#                           cache_fn_url(self.url))
#         write_pickled_repodata(cache_path, self._data)
#
#     def query(self, query):
#         """query information about a package"""
#         raise NotImplemented
#
#     def contains(self, package_ref):
#         """Check whether the package is contained in this channel."""
#         raise NotImplemented
#
#     def validate(self, package_ref):
#         """Check whether the package could be added to this channel."""
#         raise NotImplemented
#
#     def add(self, package_ref):
#         """Add the given package-ref to this channel."""
#         raise NotImplemented
#
#     def remove(self, package_ref):
#         """Remove the given package-ref from this channel."""
#         raise NotImplemented
#
#     @property
#     def index(self):
#         # WARNING: This method will soon be deprecated.
#         return self._data


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


def fetch_repodata_remote_request(url, etag, mod_stamp):
    if not context.ssl_verify:
        warnings.simplefilter('ignore', InsecureRequestWarning)

    session = CondaSession()

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

        saved_fields = {'_url': url}
        add_http_value_to_dict(resp, 'Etag', saved_fields, '_etag')
        add_http_value_to_dict(resp, 'Last-Modified', saved_fields, '_mod')
        add_http_value_to_dict(resp, 'Cache-Control', saved_fields, '_cache_control')

        # add extra values to the raw repodata json
        if json_str and json_str != "{}":
            raw_repodata_str = "%s, %s" % (
                json.dumps(saved_fields)[:-1],  # remove trailing '}'
                json_str[1:]  # remove first '{'
            )
        else:
            raw_repodata_str = json.dumps(saved_fields)
        return raw_repodata_str

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


def make_feature_record(feature_name, feature_value):
    # necessary for the SAT solver to do the right thing with features
    pkg_name = "%s=%s@" % (feature_name, feature_value)
    return IndexRecord(
        name=pkg_name,
        version='0',
        build='0',
        channel='@',
        subdir=context.subdir,
        md5="0123456789",
        provides_features={
            feature_name: feature_value,
        },
        build_number=0,
        fn=pkg_name,
    )


def collect_all_repodata_as_index(use_cache, tasks):
    index = {}
    for task in tasks:
        url, schannel, priority = task
        sd = SubdirData(Channel(url))
        index.update((Dist(prec), prec) for prec in sd.load()._package_records)
    return index


def cache_fn_url(url):
    # url must be right-padded with '/' to not invalidate any existing caches
    if not url.endswith('/'):
        url += '/'
    md5 = hashlib.md5(ensure_binary(url)).hexdigest()
    return '%s.json' % (md5[:8],)


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


def query_all(channels, subdirs, package_ref_or_match_spec):
    channel_priority_map = odict((k, v[1]) for k, v in
                                 iteritems(prioritize_channels(channels, subdirs=subdirs)))

    result = executor = None
    if context.concurrent:
        try:
            from concurrent.futures import ThreadPoolExecutor, as_completed
            executor = ThreadPoolExecutor(10)
            futures = (executor.submit(SubdirData(Channel(url), priority).query,
                                       package_ref_or_match_spec)
                       for url, priority in iteritems(channel_priority_map))
            result = tuple(concat(future.result() for future in as_completed(futures)))
        except (ImportError, RuntimeError) as e:
            # concurrent.futures is only available in Python >= 3.2 or if futures is installed
            # RuntimeError is thrown if number of threads are limited by OS
            log.debug(repr(e))
    if executor:
        executor.shutdown(wait=True)

    if result is None:
        subdir_datas = (SubdirData(Channel(url), priority)
                        for url, priority in iteritems(channel_priority_map))
        result = tuple(concat(sd.query(package_ref_or_match_spec) for sd in subdir_datas))

    return result


class SubdirDataType(type):

    # TODO: the priority mechanism here is NOT thread safe

    def __call__(cls, channel, priority=None):
        assert channel.subdir
        assert not channel.package_filename
        assert type(channel) is Channel
        cache_key = channel.url(with_credentials=True)
        if not cache_key.startswith('file://') and cache_key in SubdirData._cache_:
            return SubdirData._cache_[cache_key].set_priority(priority)
        else:
            subdir_data_instance = super(SubdirDataType, cls).__call__(channel, priority)
            SubdirData._cache_[cache_key] = subdir_data_instance
            return subdir_data_instance


@with_metaclass(SubdirDataType)
class SubdirData(object):
    _cache_ = {}

    def query(self, package_ref_or_match_spec):
        if not self._loaded:
            self.load()
        param = package_ref_or_match_spec
        if isinstance(param, MatchSpec):
            if param.get_exact_value('name'):
                package_name = param.get_exact_value('name')
                for prec in self._names_index[package_name]:
                    if param.match(prec):
                        yield prec
            elif param.get_exact_value('provides_features'):
                provides_features = param.get_exact_value('provides_features')
                candidates = concat(self._provides_features_index["%s=%s" % ftr_pair]
                                    for ftr_pair in iteritems(provides_features))
                for prec in candidates:
                    if param.match(prec):
                        yield prec
            else:
                for prec in self._package_records:
                    if param.match(prec):
                        yield prec
        else:
            # assume isinstance(param, PackageRef)
            for prec in self._names_index[param.name]:
                if prec == param:
                    yield prec

    def __init__(self, channel, priority=None):
        assert channel.subdir
        assert not channel.package_filename
        self.channel = channel
        self.url_w_subdir = self.channel.url(with_credentials=False)
        self.url_w_credentials = self.channel.url(with_credentials=True)
        self.cache_path_base = join(create_cache_dir(),
                                    splitext(cache_fn_url(self.url_w_credentials))[0])
        self._priority = Priority(priority if priority is not None else 1)
        self._loaded = False

    def set_priority(self, value):
        if value is not None:
            self._priority._priority = self._priority_value = value
        return self

    @property
    def use_cache(self):
        return False

    @property
    def cache_path_json(self):
        return self.cache_path_base + '.json'

    @property
    def cache_path_pickle(self):
        return self.cache_path_base + '.q'

    def load(self):
        _internal_state = self._load()
        self._internal_state = _internal_state
        self._package_records = _internal_state['_package_records']
        self._names_index = _internal_state['_names_index']
        self._provides_features_index = _internal_state['_provides_features_index']
        self._requires_features_index = _internal_state['_requires_features_index']
        self._priority = _internal_state['_priority']
        self._loaded = True
        return self

    def _load(self):
        try:
            mtime = getmtime(self.cache_path_json)
        except (IOError, OSError):
            log.debug("No local cache found for %s at %s", self.url_w_subdir, self.cache_path_json)
            if self.use_cache or (context.offline and not self.url_w_subdir.startswith('file://')):
                return {'packages': {}}
            else:
                mod_etag_headers = {}
        else:
            mod_etag_headers = read_mod_and_etag(self.cache_path_json)

            if self.use_cache:
                log.debug("Using cached repodata for %s at %s because use_cache=True",
                          self.url_w_subdir, self.cache_path_json)

                _internal_state = self._read_local_repdata(mod_etag_headers.get('_etag'),
                                                           mod_etag_headers.get('_mod'))
                return _internal_state

            if context.local_repodata_ttl > 1:
                max_age = context.local_repodata_ttl
            elif context.local_repodata_ttl == 1:
                max_age = get_cache_control_max_age(mod_etag_headers.get('_cache_control', ''))
            else:
                max_age = 0

            timeout = mtime + max_age - time()
            if (timeout > 0 or context.offline) and not self.url_w_subdir.startswith('file://'):
                log.debug("Using cached repodata for %s at %s. Timeout in %d sec",
                          self.url_w_subdir, self.cache_path_json, timeout)
                _internal_state = self._read_local_repdata(mod_etag_headers.get('_etag'),
                                                           mod_etag_headers.get('_mod'))
                return _internal_state

            log.debug("Local cache timed out for %s at %s",
                      self.url_w_subdir, self.cache_path_json)

        try:
            raw_repodata_str = fetch_repodata_remote_request(self.url_w_credentials,
                                                             mod_etag_headers.get('_etag'),
                                                             mod_etag_headers.get('_mod'))
        except Response304ContentUnchanged:
            log.debug("304 NOT MODIFIED for '%s'. Updating mtime and loading from disk",
                      self.url_w_subdir)
            touch(self.cache_path_json)
            _internal_state = self._read_local_repdata(mod_etag_headers.get('_etag'),
                                                       mod_etag_headers.get('_mod'))
            return _internal_state
        else:
            with open(self.cache_path_json, 'w') as fh:
                fh.write(raw_repodata_str or '{}')
            _internal_state = self._process_raw_repodata_str(raw_repodata_str)
            self._internal_state = _internal_state
            self._pickle_me()
            return _internal_state

    def _pickle_me(self):
        try:
            log.debug("Saving pickled state for %s at %s", self.url_w_subdir, self.cache_path_json)
            with open(self.cache_path_pickle, 'wb') as fh:
                pickle.dump(self._internal_state, fh, -1)  # -1 means HIGHEST_PROTOCOL
        except Exception:
            log.debug("Failed to dump pickled repodata.", exc_info=True)

    def _read_local_repdata(self, etag, mod_stamp):
        # first try reading pickled data
        _pickled_state = self._read_pickled(etag, mod_stamp)
        if _pickled_state:
            return _pickled_state

        # pickled data is bad or doesn't exist; load cached json
        log.debug("Loading raw json for %s at %s", self.url_w_subdir, self.cache_path_json)
        with open(self.cache_path_json) as fh:
            try:
                raw_repodata_str = fh.read()
            except ValueError as e:
                # ValueError: Expecting object: line 11750 column 6 (char 303397)
                log.debug("Error for cache path: '%s'\n%r", self.cache_path_json, e)
                message = dals("""
                An error occurred when loading cached repodata.  Executing
                `conda clean --index-cache` will remove cached repodata files
                so they can be downloaded again.
                """)
                raise CondaError(message)
            else:
                _internal_state = self._process_raw_repodata_str(raw_repodata_str)
                self._internal_state = _internal_state
                self._pickle_me()
                return _internal_state

    def _read_pickled(self, etag, mod_stamp):

        if not isfile(self.cache_path_pickle) or not isfile(self.cache_path_json):
            # Don't trust pickled data if there is no accompanying json data
            return None

        try:
            if isfile(self.cache_path_pickle):
                log.debug("found pickle file %s", self.cache_path_pickle)
            with open(self.cache_path_pickle, 'rb') as fh:
                _pickled_state = pickle.load(fh)
        except Exception as e:
            log.debug("Failed to load pickled repodata.", exc_info=True)
            rm_rf(self.cache_path_pickle)
            return None

        def _check_pickled_valid():
            yield _pickled_state.get('_url') == self.url_w_credentials
            yield _pickled_state.get('_schannel') == self.channel.canonical_name
            yield _pickled_state.get('_add_pip') == context.add_pip_as_python_dependency
            yield _pickled_state.get('_mod') == mod_stamp
            yield _pickled_state.get('_etag') == etag
            yield _pickled_state.get('_pickle_version') == REPODATA_PICKLE_VERSION

        if not all(_check_pickled_valid()):
            log.debug("Pickle load validation failed for %s at %s.",
                      self.url_w_subdir, self.cache_path_json)
            return None

        # assert isinstance(_internal_state['_priority'], Priority)
        # log.debug("setting priority for %s to '%d'", _internal_state.get('_url'), priority)
        # _internal_state['_priority']._priority = priority

        return _pickled_state

    def _process_raw_repodata_str(self, raw_repodata_str):
        json_obj = json.loads(raw_repodata_str or '{}')

        subdir = json_obj.get('info', {}).get('subdir') or self.channel.subdir
        assert subdir == self.channel.subdir
        add_pip = context.add_pip_as_python_dependency
        priority = self._priority
        schannel = self.channel.canonical_name

        self._package_records = _package_records = []
        self._names_index = _names_index = defaultdict(list)
        self._provides_features_index = _provides_features_index = defaultdict(list)
        self._requires_features_index = _requires_features_index = defaultdict(list)

        _internal_state = {
            'channel': self.channel,
            'url_w_subdir': self.url_w_subdir,
            'url_w_credentials': self.url_w_credentials,
            'cache_path_base': self.cache_path_base,

            '_package_records': _package_records,
            '_names_index': _names_index,
            '_provides_features_index': _provides_features_index,
            '_requires_features_index': _requires_features_index,

            '_etag': json_obj.get('_etag'),
            '_mod': json_obj.get('_mod'),
            '_cache_control': json_obj.get('_cache_control'),
            '_url': json_obj.get('_url'),
            '_add_pip': add_pip,
            '_pickle_version': REPODATA_PICKLE_VERSION,
            '_priority': priority,
            '_schannel': schannel,
        }

        meta_in_common = {  # just need to make this once, then apply with .update()
            'arch': json_obj.get('info', {}).get('arch'),
            'channel': self.channel,
            'platform': json_obj.get('info', {}).get('platform'),
            'priority': priority,
            'schannel': schannel,
            'subdir': subdir,
        }

        channel_url = self.url_w_credentials
        for fn, info in iteritems(json_obj.get('packages', {})):
            info['fn'] = fn
            info['url'] = join_url(channel_url, fn)
            if add_pip and info['name'] == 'python' and info['version'].startswith(('2.', '3.')):
                info['depends'].append('pip')
            info.update(meta_in_common)
            package_record = PackageRecord(**info)

            _package_records.append(package_record)
            _names_index[package_record.name].append(package_record)
            for ftr_name, ftr_value in iteritems(package_record.provides_features):
                _provides_features_index["%s=%s" % (ftr_name, ftr_value)].append(package_record)
            for ftr_name, ftr_value in iteritems(package_record.requires_features):
                _requires_features_index["%s=%s" % (ftr_name, ftr_value)].append(package_record)

        # for feature_name, feature_values in iteritems(all_features):
        #     for feature_value in feature_values:
        #         rec = make_feature_record(feature_name, feature_value)
        #         packages[Dist(rec)] = rec
        self._internal_state = _internal_state
        return _internal_state
