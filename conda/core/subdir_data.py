# -*- coding: utf-8 -*-
# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
from __future__ import absolute_import, division, print_function, unicode_literals

from collections import defaultdict
from contextlib import closing
from datetime import datetime
from errno import EACCES, ENODEV, EPERM
from genericpath import getmtime, isfile
import hashlib
import json
from logging import DEBUG, getLogger
from mmap import ACCESS_READ, mmap
from os.path import dirname, isdir, join
import re
from time import time
import warnings

from .. import CondaError
from .._vendor.auxlib.ish import dals
from .._vendor.auxlib.logz import stringify
from .._vendor.toolz import concat, concatv, get, take
from ..base.constants import CONDA_PACKAGE_EXTENSION_V1
from ..base.context import context
from ..common.compat import (ensure_binary, ensure_text_type, ensure_unicode, iteritems, iterkeys,
                             open, string_types, text_type, with_metaclass)
from ..common.io import ThreadLimitedThreadPoolExecutor, as_completed
from ..common.url import join_url
from ..core.package_cache_data import PackageCacheData
from ..exceptions import CondaDependencyError, CondaUpgradeError, NotWritableError
from ..gateways.connection import (ConnectionError, HTTPError, InsecureRequestWarning,
                                   InvalidSchema, SSLError)
from ..gateways.connection.session import CondaSession
from ..gateways.disk import mkdir_p, mkdir_p_sudo_safe
from ..gateways.disk.delete import rm_rf
from ..gateways.disk.update import touch
from ..models.channel import Channel, all_channel_urls
from ..models.match_spec import MatchSpec
from ..models.records import PackageRecord

try:
    import cPickle as pickle
except ImportError:  # pragma: no cover
    import pickle  # NOQA

log = getLogger(__name__)
stderrlog = getLogger('conda.stderrlog')

INTERNAL_PICKLE_VERSION = 35
MAX_REPODATA_VERSION = 1
REPODATA_HEADER_RE = b'"(_etag|_mod|_cache_control)":[ ]?"(.*?[^\\\\])"[,\}\s]'  # NOQA


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
            assert isinstance(param, PackageRecord)
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
        self.cache_dir = create_cache_dir()
        self._loaded = False

    def reload(self):
        self._loaded = False
        self.load()
        return self

    def load(self):
        try:
            # 1. Try pulling lastmodified.json
            cached_lastmodified = load_url_object(
                self.cache_dir,
                join_url(self.url_w_credentials, "lastmodified.json"),
                self.channel,
                CachedLastModified
            )
            if cached_lastmodified:
                self._names_index = cached_lastmodified._names_index
                self._track_features_index = cached_lastmodified._track_features_index
                self._package_records = cached_lastmodified  # implemented with __iter__
            else:
                self._package_records = []
                self._names_index = {}
                self._track_features_index = {}
        except ResponseException as e:
            log.info("falling back to repodata.json for %s due to %r", self.url_w_subdir, e)

            # 2. If that fails, try repodata.json
            try:
                cached_repodata = load_url_object(
                    self.cache_dir,
                    join_url(self.url_w_credentials, "repodata.json"),
                    self.channel,
                    CachedRepodata
                )
            except ResponseException as e:
                # TODO: Add in litany of error messages here
                raise
            else:
                if cached_repodata.content.get("repodata_version", 0) > MAX_REPODATA_VERSION:
                    raise CondaUpgradeError(dals("""
                        The current version of conda is too old to read repodata from
        
                            %s
        
                        (This version only supports repodata_version 1.)
                        Please update conda to use this channel.
                        """) % self.url_w_subdir)
                self._package_records = cached_repodata.content['_package_records']
                self._names_index = cached_repodata.content['_names_index']
                self._track_features_index = cached_repodata.content['_track_features_index']

        self._loaded = True
        return self

    def iter_records(self):
        if not self._loaded:
            self.load()
        return iter(self._package_records)


def read_etag_and_mod(path):
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


class ResponseException(Exception):

    def __init__(self, url, response_code, response):
        super(ResponseException, self).__init__()
        self.url = url
        self.response_code = response_code
        self.response = response


def load_url_object(cache_dir, url, channel, cache_cls, etag=None, mod=None):
    log.debug("loading url %s", url)
    cache_base_fn = hashlib.md5(ensure_binary(url)).hexdigest()[:12]
    cache_path_base = join(cache_dir, cache_base_fn)
    cache_path_json = cache_path_base + ".json"
    _incoming_etag_mod = {}
    if etag:
        _incoming_etag_mod["_etag"] = etag
    if mod:
        _incoming_etag_mod["_mod"] = mod

    try:
        mtime = getmtime(cache_path_json)
    except EnvironmentError:
        if context.use_index_cache or (context.offline and not url.startswith('file://')):
            log.debug("Using cached data for %s at %s forced. Returning empty content.",
                      url, cache_path_json)
            return None
        else:
            etag_mod_headers = {}
    else:
        etag_mod_headers = read_etag_and_mod(cache_path_json)
        # update etag and mod with incoming values only if the .json file already exists in cache
        if "_etag" in etag_mod_headers and etag:
            etag_mod_headers["_etag"] = etag
        if "_mod" in etag_mod_headers and mod:
            etag_mod_headers["_mod"] = mod
        etag, mod = etag_mod_headers.get('_etag'), etag_mod_headers.get('_mod')
        cache_control = etag_mod_headers.get('_cache_control')
        if context.use_index_cache:
            log.debug("Using cached content for %s at %s because context.use_index_cache == True",
                      url, cache_path_json)
            return cache_cls.load_from_cache(
                cache_path_base, channel, url, etag, mod, cache_control
            )
        if context.local_repodata_ttl > 1:
            max_age = context.local_repodata_ttl
        elif context.local_repodata_ttl == 1:
            max_age = get_cache_control_max_age(etag_mod_headers.get('_cache_control', ''))
        else:
            max_age = 0

        timeout = mtime + max_age - time()
        if (timeout > 0 or context.offline) and not url.startswith('file://'):
            log.debug("Using cached repodata for %s at %s. Timeout in %d sec",
                      url, cache_path_json, timeout)
            return cache_cls.load_from_cache(
                cache_path_base, channel, url, etag, mod, cache_control
            )
        log.debug("Local cache timed out for %s at %s", url, cache_path_json)

    etag, mod = etag_mod_headers.get('_etag'), etag_mod_headers.get('_mod')
    cache_control = etag_mod_headers.get('_cache_control')
    try:
        raw_content_str, saved_fields = fetch_remote_request(url, etag, mod)
    except ResponseException as e:
        if e.response_code == 304:
            log.debug("304 NOT MODIFIED for '%s'. Updating mtime and loading from disk", url)
            touch(cache_path_json)
            return cache_cls.load_from_cache(
                cache_path_base, channel, url, etag, mod, cache_control
            )
        else:
            raise
    else:
        if not isdir(dirname(cache_path_json)):
            mkdir_p(dirname(cache_path_json))
        try:
            with open(cache_path_json, "w") as fh:
                fh.write(raw_content_str)
        except EnvironmentError as e:
            if e.errno in (EACCES, EPERM):
                raise NotWritableError(cache_path_json, e.errno, caused_by=e)
            else:
                raise

        etag, mod, cache_control = get(["_etag", "_mod", "_cache_control"], saved_fields, None)
        cached_obj = cache_cls(
            cache_path_base, channel, url, etag, mod, cache_control, raw_content_str
        )
        cached_obj.write_pickle()
        return cached_obj


class PickledObject(object):

    def __init__(self, cache_path_base, channel, url, etag, mod, cache_control, raw_content_str):
        self.cache_path_base = cache_path_base
        self.channel = channel
        self.url = url

        self.mod = mod
        self.etag = etag
        self.cache_control = cache_control

        self.internal_pickle_version = INTERNAL_PICKLE_VERSION
        self.content = self.process(raw_content_str)

    def process(self, raw_content_str):
        return raw_content_str

    @classmethod
    def load_from_cache(cls, cache_path_base, channel, url, etag, mod, cache_control):
        # first try reading pickled data
        cached_obj = cls._load_from_pickle(cache_path_base, url, etag, mod)
        if cached_obj:
            return cached_obj

        # pickled data is bad or doesn't exist; load cached json
        cache_path_json = cache_path_base + ".json"
        log.debug("Loading raw json for %s at %s", url, cache_path_json)
        with open(cache_path_json) as fh:
            try:
                raw_content_str = fh.read()
            except ValueError as e:
                # ValueError: Expecting object: line 11750 column 6 (char 303397)
                log.debug("Error for cache path: '%s'\n%r", cache_path_json, e)
                message = dals("""
                       An error occurred when loading cached repodata.  Executing
                       `conda clean --index-cache` will remove cached repodata files
                       so they can be downloaded again.
                       """)
                raise CondaError(message)
            else:
                cached_obj = cls(
                    cache_path_base, channel, url, etag, mod, cache_control, raw_content_str
                )
                cached_obj.write_pickle()
                return cached_obj

    @classmethod
    def _load_from_pickle(cls, cache_path_base, url, etag, mod):
        cache_path_json = cache_path_base + ".json"
        cache_path_pickle = cache_path_base + ".q"
        if not isfile(cache_path_pickle) or not isfile(cache_path_json):
            # Don't trust pickled data if there is no accompanying json data
            log.debug("pickle file '%s' does not have accompanying json file", cache_path_pickle)
            return None
        try:
            if isfile(cache_path_pickle):
                log.debug("found pickle file %s", cache_path_pickle)
            with open(cache_path_pickle, "rb") as fh:
                po = pickle.load(fh)
        except Exception:
            log.debug("Failed to load pickled repodata.", exc_info=True)
            rm_rf(cache_path_pickle)
            return None

        check_failures = False
        if not isinstance(po, cls):
            log.debug("Pickle load validation failed for %s at %s due to %r != %r.",
                      url, cache_path_base + ".q", po, cls)
            check_failures = True
        if po.url != url:
            log.debug("Pickle load validation failed for %s at %s due to %r != %r.",
                      url, cache_path_base + ".q", po.url, url)
            check_failures = True
        if (po.etag or etag) and _extract_etag_value(po.etag) != _extract_etag_value(etag):
            log.debug("Pickle load validation failed for %s at %s due to %r != %r.",
                      url, cache_path_base + ".q", po.etag, etag)
            check_failures = True
        if po.mod != mod:
            log.debug("Pickle load validation failed for %s at %s due to %r != %r.",
                      url, cache_path_base + ".q", po.mod, mod)
            check_failures = True
        if po.internal_pickle_version != INTERNAL_PICKLE_VERSION:
            log.debug("Pickle load validation failed for %s at %s due to %r != %r.",
                      url, cache_path_base + ".q",
                      po.internal_pickle_version, INTERNAL_PICKLE_VERSION)
            check_failures = True
        if check_failures:
            return None

        return po

    def write_pickle(self):
        cache_path_pickle = self.cache_path_base + ".q"
        try:
            log.debug("Saving pickled state for %s at %s", self.url, cache_path_pickle)
            with open(cache_path_pickle, "wb") as fh:
                pickle.dump(self, fh, -1)  # -1 means HIGHEST_PROTOCOL
        except Exception:
            log.debug("Failed to dump pickled repodata.", exc_info=True)


class CachedRepodata(PickledObject):

    def process(self, raw_content_str):
        json_obj = (
            json.loads(raw_content_str)
            if isinstance(raw_content_str, string_types)
            else raw_content_str
        )
        subdir = json_obj.get('info', {}).get('subdir') or self.channel.subdir
        assert subdir == self.channel.subdir
        schannel = self.channel.canonical_name

        self._package_records = _package_records = []
        self._names_index = _names_index = defaultdict(list)
        self._track_features_index = _track_features_index = defaultdict(list)

        content = {
            '_package_records': _package_records,
            '_names_index': _names_index,
            '_track_features_index': _track_features_index,
            'repodata_version': json_obj.get('repodata_version', 0),
        }
        if content["repodata_version"] > MAX_REPODATA_VERSION:
            raise CondaUpgradeError(dals("""
                The current version of conda is too old to read repodata from

                    %s

                (This version only supports repodata_version 1.)
                Please update conda to use this channel.
                """) % self.url)

        meta_in_common = {  # just need to make this once, then apply with .update()
            'arch': json_obj.get('info', {}).get('arch'),
            'channel': self.channel,
            'platform': json_obj.get('info', {}).get('platform'),
            'schannel': schannel,
            'subdir': subdir,
        }

        channel_url = self.channel.url(with_credentials=True)
        legacy_packages = json_obj.get("packages", {})
        conda_packages = json_obj.get("packages.conda", {})
        _tar_bz2 = CONDA_PACKAGE_EXTENSION_V1
        use_these_legacy_keys = set(iterkeys(legacy_packages)) - set(
            k[:-6] + _tar_bz2 for k in iterkeys(conda_packages)
        )

        for fn, info in concatv(
            iteritems(conda_packages),
            ((k, legacy_packages[k]) for k in use_these_legacy_keys),
        ):
            if info.get('record_version', 0) > 1:
                log.debug("Ignoring record_version %d from %s",
                          info["record_version"], info['url'])
                continue
            info['fn'] = fn
            info['url'] = join_url(channel_url, fn)
            info.update(meta_in_common)
            package_record = PackageRecord(**info)

            _package_records.append(package_record)
            _names_index[package_record.name].append(package_record)
            for ftr_name in package_record.track_features:
                _track_features_index[ftr_name].append(package_record)
        return content


class CallableAsItemGetter(object):
    def __init__(self, callable_):
        self._callable = callable_

    def __getitem__(self, item):
        return self._callable(item)


class CachedLastModified(PickledObject):

    def __init__(self, cache_path_base, channel, url, etag, mod, cache_control, raw_content_str):
        super(CachedLastModified, self).__init__(
            cache_path_base, channel, url, etag, mod, cache_control, raw_content_str
        )
        self._names_index = CallableAsItemGetter(self.load_by_name)
        self._track_features_index = CallableAsItemGetter(self.load_by_track_features)
        self._cached_repodata = {}

    def process(self, raw_content_str):
        json_obj = (
            json.loads(raw_content_str)
            if isinstance(raw_content_str, string_types)
            else raw_content_str
        )
        subdir = json_obj.get('info', {}).get('subdir') or self.channel.subdir
        assert subdir == self.channel.subdir

        self._package_names = _package_names = json_obj.get("packages", {})
        content = {
            '_package_names': _package_names,
            'lastmodified_version': json_obj.get('lastmodified_version', 0),
        }
        if content["lastmodified_version"] > MAX_REPODATA_VERSION:
            raise CondaUpgradeError(dals("""
                The current version of conda is too old to read repodata from

                    %s

                (This version only supports repodata_version 1.)
                Please update conda to use this channel.
                """) % self.url)
        return content

    def _get_cache_key_shard(self, key):
        cached_repodata_shard = self._cached_repodata.get(key, None)
        if not cached_repodata_shard:
            cache_details = self._package_names.get(key)
            if cache_details:
                etag = '"%s"' % cache_details["etag"]
                mod = datetime.utcfromtimestamp(
                    cache_details["mod"]
                ).strftime("%a, %d %b %Y %H:%M:%S GMT")
                url = join_url(self.channel.url(with_credentials=True), key + ".json")
                self._cached_repodata[key] = cached_repodata_shard = load_url_object(
                    dirname(self.cache_path_base),
                    url,
                    self.channel,
                    CachedRepodata,
                    etag,
                    mod
                )
        return cached_repodata_shard

    def load_by_name(self, name):
        cached_repodata_shard = self._get_cache_key_shard(name)
        if cached_repodata_shard:
            return cached_repodata_shard.content["_names_index"][name]
        else:
            return []

    def load_by_track_features(self, feat):
        cached_repodata_shard = self._get_cache_key_shard(feat)
        if cached_repodata_shard:
            return cached_repodata_shard.content["_track_features_index"][feat]
        else:
            return []

    def load_all_package_records(self):
        key = "__all_package_records"
        _package_records = self._cached_repodata.get(key, None)
        if _package_records is None:
            url = join_url(self.channel.url(with_credentials=True), "repodata.json")
            cached_repodata = load_url_object(
                dirname(self.cache_path_base),
                url,
                self.channel,
                CachedRepodata
            )
            if cached_repodata:
                if cached_repodata.content.get("repodata_version", 0) > MAX_REPODATA_VERSION:
                    raise CondaUpgradeError(dals("""
                        The current version of conda is too old to read repodata from
        
                            %s
        
                        (This version only supports repodata_version 1.)
                        Please update conda to use this channel.
                        """) % url)
                _package_records = cached_repodata.content['_package_records']
            else:
                _package_records = []
            self._cached_repodata[key] = _package_records
        return _package_records

    def __iter__(self):
        return iter(self.load_all_package_records())


def fetch_remote_request(url, etag, mod):
    if not context.ssl_verify:
        warnings.simplefilter('ignore', InsecureRequestWarning)

    session = CondaSession()

    headers = {}
    if etag:
        headers["If-None-Match"] = etag
    if mod:
        headers["If-Modified-Since"] = mod
    headers['Accept-Encoding'] = 'gzip, deflate, compress, identity'
    headers['Content-Type'] = 'application/json'

    try:
        timeout = context.remote_connect_timeout_secs, context.remote_read_timeout_secs
        resp = session.get(url, headers=headers, proxies=session.proxies, timeout=timeout)
        if log.isEnabledFor(DEBUG):
            log.debug(stringify(resp, content_max_len=256))
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
        # is_noarch = url.split("/")[-2] == "noarch"
        response_code = getattr(e.response, 'status_code', None)
        raise ResponseException(url, response_code, e.response)
    if resp.status_code == 304:
        raise ResponseException(url, resp.status_code, resp)

    raw_json_str = ensure_text_type(resp.content).strip()

    saved_fields = {'_url': url}
    add_http_value_to_dict(resp, 'Etag', saved_fields, '_etag')
    add_http_value_to_dict(resp, 'Last-Modified', saved_fields, '_mod')
    add_http_value_to_dict(resp, 'Cache-Control', saved_fields, '_cache_control')

    if not raw_json_str or raw_json_str == "{}":
        raw_content_str = json.dumps(saved_fields)
    elif raw_json_str[0] != "{" or raw_json_str[-1] != "}":
        log.warning("Content for url '%s' is invalid. Considering as empty.", url)
        raw_content_str = json.dumps(saved_fields)
    else:
        # add extra values to the raw repodata json
        raw_content_str = "%s, %s" % (
            json.dumps(saved_fields)[:-1],  # remove trailing '}'
            raw_json_str[1:]  # remove first '{'
        )
    return raw_content_str, saved_fields


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

def add_http_value_to_dict(resp, http_key, d, dict_key):
    value = resp.headers.get(http_key)
    if value:
        d[dict_key] = value


def create_cache_dir():
    cache_dir = join(PackageCacheData.first_writable(context.pkgs_dirs).pkgs_dir, 'cache')
    mkdir_p_sudo_safe(cache_dir)
    return cache_dir


def _extract_etag_value(etag):
    if etag:
        match = re.match(r'(?:W/)?"([-_\w\d]+)"', etag)
        if match:
            return match.groups()[0]
    return None


if __name__ == "__main__":
    context.__init__()
    from ..cli.main import init_loggers
    init_loggers(context)
    print(list(SubdirData(Channel("http://conda.rocks/repo/mewtwo/win-64")).query("zlib")))
    # print(list(SubdirData(Channel("http://repo.anaconda.com/pkgs/main/win-64")).query("zlib")))