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

from conda import config
from conda.utils import memoized
from conda.connection import connectionhandled_urlopen
from conda.compat import itervalues, get_http_value
from conda.lock import Locked

import requests

log = getLogger(__name__)
dotlog = getLogger('dotupdate')
stdoutlog = getLogger('stdoutlog')

fail_unknown_host = False
retries = 3


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

    session = session or requests.session()

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
        resp = session.get(url + 'repodata.json.bz2', headers=headers)
        resp.raise_for_status()
        if resp.status_code != 304:
            cache = json.loads(bz2.decompress(resp.content).decode('utf-8'))

    except ValueError:
        raise RuntimeError("Invalid index file: %srepodata.json.bz2" % url)

    except requests.exceptions.HTTPError as e:
        msg = "HTTPError: %s: %s\n" % (e, url)
        log.debug(msg)
        raise RuntimeError(msg)

    cache['_url'] = url
    try:
        with open(cache_path, 'w') as fo:
            json.dump(cache, fo, indent=2, sort_keys=True)
    except IOError:
        pass

    return cache or None


@memoized
def fetch_index(channel_urls, use_cache=False, unknown=False):
    log.debug('channel_urls=' + repr(channel_urls))
    index = {}
    stdoutlog.info("Fetching package metadata: ")
    session = requests.session()
    for url in reversed(channel_urls):
        repodata = fetch_repodata(url, use_cache=use_cache, session=session)
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

    session = session or requests.session()

    fn = '%(name)s-%(version)s-%(build)s.tar.bz2' % info
    url = info['channel'] + fn
    log.debug("url=%r" % url)
    path = join(dst_dir, fn)
    pp = path + '.part'

    with Locked(dst_dir):
        for x in range(retries):
            try:
                resp = session.get(url, stream=True)
            except IOError:
                log.debug("attempt %d failed at urlopen" % x)
                continue
            n = 0
            h = hashlib.new('md5')
            getLogger('fetch.start').info((fn, info['size']))
            need_retry = False
            try:
                fo = open(pp, 'wb')
            except IOError:
                raise RuntimeError("Could not open %r for writing.  "
                          "Permissions problem or missing directory?" % pp)

            for chunk in resp.iter_content(16384):
                try:
                    fo.write(chunk)
                except IOError:
                    raise RuntimeError("Failed to write to %r." % pp)
                h.update(chunk)
                n += len(chunk)
                getLogger('fetch.update').info(n)

            fo.close()
            if need_retry:
                continue

            getLogger('fetch.stop').info(None)
            if h.hexdigest() != info['md5']:
                raise RuntimeError("MD5 sums mismatch for download: %s (%s != %s)" % (fn, h.hexdigest(), info['md5']))
            try:
                os.rename(pp, path)
            except OSError:
                raise RuntimeError("Could not rename %r to %r." % (pp, path))
            try:
                with open(join(dst_dir, 'urls.txt'), 'a') as fa:
                    fa.write('%s\n' % url)
            except IOError:
                pass
            return

    raise RuntimeError("Could not locate '%s'" % url)


def download(url, dst_path):
    try:
        u = connectionhandled_urlopen(url)
    except IOError:
        raise RuntimeError("Could not open '%s'" % url)
    except ValueError as e:
        raise RuntimeError(e)

    size = get_http_value(u, 'Content-Length')
    if size:
        size = int(size)
        fn = basename(dst_path)
        getLogger('fetch.start').info((fn[:14], size))

    n = 0
    fo = open(dst_path, 'wb')
    while True:
        chunk = u.read(16384)
        if not chunk:
            break
        fo.write(chunk)
        n += len(chunk)
        if size:
            getLogger('fetch.update').info(n)
    fo.close()

    u.close()
    if size:
        getLogger('fetch.stop').info(None)


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
