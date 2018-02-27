# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function, unicode_literals

import bz2
from collections import defaultdict
from contextlib import closing
from errno import EACCES, ENODEV, EPERM
from genericpath import getmtime, isfile
import hashlib
import json
from logging import DEBUG, getLogger
from mmap import ACCESS_READ, mmap
from os.path import dirname, isdir, join, splitext
import re
from textwrap import dedent
from time import time
import warnings

from .. import CondaError
from .._vendor.auxlib.ish import dals
from .._vendor.auxlib.logz import stringify
from ..base.constants import CONDA_HOMEPAGE_URL
from ..base.context import context
from ..common.compat import (ensure_binary, ensure_text_type, ensure_unicode, iteritems,
                             string_types, text_type, with_metaclass)
from ..common.io import ThreadLimitedThreadPoolExecutor, as_completed
from ..common.url import join_url, maybe_unquote
from ..core.package_cache_data import PackageCacheData
from ..exceptions import CondaDependencyError, CondaHTTPError, NotWritableError
from ..gateways.connection import (ConnectionError, HTTPError, InsecureRequestWarning,
                                   InvalidSchema, SSLError)
from ..gateways.connection.session import CondaSession
from ..gateways.disk import mkdir_p, mkdir_p_sudo_safe
from ..gateways.disk.delete import rm_rf
from ..gateways.disk.update import touch
from ..models.channel import Channel, all_channel_urls
from ..models.dist import Dist
from ..models.match_spec import MatchSpec
from ..models.records import PackageRecord, PackageRef

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

REPODATA_PICKLE_VERSION = 18
REPODATA_HEADER_RE = b'"(_etag|_mod|_cache_control)":[ ]?"(.*?[^\\\\])"[,\}\s]'


class SubdirDataType(type):

    def __call__(cls, channel):
        assert channel.subdir
        assert not channel.package_filename
        assert type(channel) is Channel
        cache_key = channel.url(with_credentials=True)
        if not cache_key.startswith('file://') and cache_key in SubdirData._cache_:
            return SubdirData._cache_[cache_key]

        subdir_data_instance = super(SubdirDataType, cls).__call__(channel)
        SubdirData._cache_[cache_key] = subdir_data_instance
        return subdir_data_instance


@with_metaclass(SubdirDataType)
class SubdirData(object):
    _cache_ = {}

    @staticmethod
    def query_all(package_ref_or_match_spec, channels=None, subdirs=None):
        from .index import check_whitelist  # TODO: fix in-line import
        if channels is None:
            channels = context.channels
        if subdirs is None:
            subdirs = context.subdirs
        channel_urls = all_channel_urls(channels, subdirs=subdirs)
        check_whitelist(channel_urls)
        with ThreadLimitedThreadPoolExecutor() as executor:
            futures = tuple(executor.submit(
                SubdirData(Channel(url)).query, package_ref_or_match_spec
            ) for url in channel_urls)
            return tuple(concat(future.result() for future in as_completed(futures)))

    def query(self, package_ref_or_match_spec):
        if not self._loaded:
            self.load()
        param = package_ref_or_match_spec
        if isinstance(param, string_types):
            param = MatchSpec(param)
        if isinstance(param, MatchSpec):
            if param.get_exact_value('name'):
                package_name = param.get_exact_value('name')
                for prec in self._names_index[package_name]:
                    if param.match(prec):
                        yield prec
            elif param.get_exact_value('track_features'):
                track_features = param.get_exact_value('track') or ()
                candidates = concat(self._track_features_index[feature_name]
                                    for feature_name in track_features)
                for prec in candidates:
                    if param.match(prec):
                        yield prec
            else:
                for prec in self._package_records:
                    if param.match(prec):
                        yield prec
        else:
            assert isinstance(param, PackageRef)
            for prec in self._names_index[param.name]:
                if prec == param:
                    yield prec

    def __init__(self, channel):
        assert channel.subdir
        if channel.package_filename:
            parts = channel.dump()
            del parts['package_filename']
            channel = Channel(**parts)
        self.channel = channel
        self.url_w_subdir = self.channel.url(with_credentials=False)
        self.url_w_credentials = self.channel.url(with_credentials=True)
        self.cache_path_base = join(create_cache_dir(),
                                    splitext(cache_fn_url(self.url_w_credentials))[0])
        self._loaded = False

    def reload(self):
        self._loaded = False
        self.load()
        return self

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
        self._package_dists = _internal_state['_package_dists']  # only needed as an optimization for conda-build  # NOQA
        self._names_index = _internal_state['_names_index']
        self._track_features_index = _internal_state['_track_features_index']
        self._loaded = True
        return self

    def iter_records(self):
        if not self._loaded:
            self.load()
        return iter(self._package_records)

    def iter_dists_records(self):
        if not self._loaded:
            self.load()
        return zip(self._package_dists, self._package_records)

    def _load(self):
        try:
            mtime = getmtime(self.cache_path_json)
        except (IOError, OSError):
            log.debug("No local cache found for %s at %s", self.url_w_subdir, self.cache_path_json)
            if context.use_index_cache or (context.offline
                                           and not self.url_w_subdir.startswith('file://')):
                log.debug("Using cached data for %s at %s forced. Returning empty repodata.",
                          self.url_w_subdir, self.cache_path_json)
                return {
                    '_package_records': (),
                    '_package_dists': (),
                    '_names_index': defaultdict(list),
                    '_track_features_index': defaultdict(list),
                }
            else:
                mod_etag_headers = {}
        else:
            mod_etag_headers = read_mod_and_etag(self.cache_path_json)

            if context.use_index_cache:
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
            if not isdir(dirname(self.cache_path_json)):
                mkdir_p(dirname(self.cache_path_json))
            try:
                with open(self.cache_path_json, 'w') as fh:
                    fh.write(raw_repodata_str or '{}')
            except (IOError, OSError) as e:
                if e.errno in (EACCES, EPERM):
                    raise NotWritableError(self.cache_path_json, e.errno, caused_by=e)
                else:
                    raise
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

        return _pickled_state

    def _process_raw_repodata_str(self, raw_repodata_str):
        json_obj = json.loads(raw_repodata_str or '{}')

        subdir = json_obj.get('info', {}).get('subdir') or self.channel.subdir
        assert subdir == self.channel.subdir
        add_pip = context.add_pip_as_python_dependency
        schannel = self.channel.canonical_name

        self._package_records = _package_records = []
        self._package_dists = _package_dists = []  # creating and caching these here is an optimization for conda-build  # NOQA
        self._names_index = _names_index = defaultdict(list)
        self._track_features_index = _track_features_index = defaultdict(list)

        _internal_state = {
            'channel': self.channel,
            'url_w_subdir': self.url_w_subdir,
            'url_w_credentials': self.url_w_credentials,
            'cache_path_base': self.cache_path_base,

            '_package_records': _package_records,
            '_package_dists': _package_dists,
            '_names_index': _names_index,
            '_track_features_index': _track_features_index,

            '_etag': json_obj.get('_etag'),
            '_mod': json_obj.get('_mod'),
            '_cache_control': json_obj.get('_cache_control'),
            '_url': json_obj.get('_url'),
            '_add_pip': add_pip,
            '_pickle_version': REPODATA_PICKLE_VERSION,
            '_schannel': schannel,
        }

        meta_in_common = {  # just need to make this once, then apply with .update()
            'arch': json_obj.get('info', {}).get('arch'),
            'channel': self.channel,
            'platform': json_obj.get('info', {}).get('platform'),
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
            _package_dists.append(Dist(package_record))
            _names_index[package_record.name].append(package_record)
            for ftr_name in package_record.track_features:
                _track_features_index[ftr_name].append(package_record)

        self._internal_state = _internal_state
        return _internal_state


def read_mod_and_etag(path):
    with open(path, 'rb') as f:
        try:
            with closing(mmap(f.fileno(), 0, access=ACCESS_READ)) as m:
                match_objects = take(3, re.finditer(REPODATA_HEADER_RE, m))
                result = dict(map(ensure_unicode, mo.groups()) for mo in match_objects)
                return result
        except (BufferError, ValueError, OSError):  # pragma: no cover
            # BufferError: cannot close exported pointers exist
            #   https://github.com/conda/conda/issues/4592
            # ValueError: cannot mmap an empty file
            return {}
        except (IOError, OSError) as e:  # pragma: no cover
            # OSError: [Errno 19] No such device
            if e.errno == ENODEV:
                return {}
            raise


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

    if 'repo.anaconda.com' in url:
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
        if status_code in (403, 404):
            if not url.endswith('/noarch'):
                return None
            else:
                if context.allow_non_channel_urls:
                    help_message = dedent("""
                    WARNING: The remote server could not find the noarch directory for the
                    requested channel with url: %s

                    It is possible you have given conda an invalid channel. Please double-check
                    your conda configuration using `conda config --show channels`.

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
                    Use `conda config --show channels` to view your configuration's current state.
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
            A remote server error occurred when trying to retrieve this URL.

            A 500-type error (e.g. 500, 501, 502, 503, etc.) indicates the server failed to
            fulfill a valid request.  The problem may be spurious, and will resolve itself if you
            try your request again.  If the problem persists, consider notifying the maintainer
            of the remote server.
            """)

        else:
            if url.startswith("https://repo.anaconda.com/"):
                help_message = dals("""
                An HTTP error occurred when trying to retrieve this URL.
                HTTP errors are often intermittent, and a simple retry will get you on your way.

                If your current network has https://www.anaconda.com blocked, please file
                a support request with your network engineering team.

                %s
                """) % maybe_unquote(repr(e))
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
                             e.response,
                             caused_by=e)

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


def make_feature_record(feature_name):
    # necessary for the SAT solver to do the right thing with features
    pkg_name = "%s@" % feature_name
    return PackageRecord(
        name=pkg_name,
        version='0',
        build='0',
        channel='@',
        subdir=context.subdir,
        md5="12345678901234567890123456789012",
        track_features=(feature_name,),
        build_number=0,
        fn=pkg_name,
    )


def collect_all_repodata_as_index(use_cache, channel_urls):
    index = {}
    for url in channel_urls:
        sd = SubdirData(Channel(url))
        index.update(sd.iter_dists_records())
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
    cache_dir = join(PackageCacheData.first_writable(context.pkgs_dirs).pkgs_dir, 'cache')
    mkdir_p_sudo_safe(cache_dir)
    return cache_dir
