# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function, unicode_literals

import hashlib
import os
import requests
import sys
import tarfile
import warnings
from logging import getLogger
from os.path import basename, dirname, exists, isdir, isfile, join

from ..base.constants import DEFAULTS
from ..base.context import context
from ..common.disk import exp_backoff_fn, rm_rf
from ..common.url import path_to_url, maybe_add_auth
from ..connection import CondaSession, RETRIES
from ..exceptions import CondaRuntimeError, CondaSignatureError, MD5MismatchError
from ..lock import FileLock
from ..models.channel import Channel, offline_keep
from ..models.dist import Dist

log = getLogger(__name__)
stderrlog = getLogger('stderrlog')



# ------- package cache ----- construction

# The current package cache does not support the ability to store multiple packages
# with the same filename from different channels. Furthermore, the filename itself
# cannot be used to disambiguate; we must read the URL from urls.txt to determine
# the source channel. For this reason, we now fully parse the directory and its
# accompanying urls.txt file so we can make arbitrary queries without having to
# read this data multiple times.

package_cache_ = {}
fname_table_ = {}


def add_cached_package(pdir, url, overwrite=False, urlstxt=False):
    """
    Adds a new package to the cache. The URL is used to determine the
    package filename and channel, and the directory pdir is scanned for
    both a compressed and an extracted version of that package. If
    urlstxt=True, this URL will be appended to the urls.txt file in the
    cache, so that subsequent runs will correctly identify the package.
    """
    package_cache()
    if '/' in url:
        dist = url.rsplit('/', 1)[-1]
    else:
        dist = url
        url = None
    if dist.endswith('.tar.bz2'):
        fname = dist
        dist = dist[:-8]
    else:
        fname = dist + '.tar.bz2'
    xpkg = join(pdir, fname)
    if not overwrite and xpkg in fname_table_:
        return
    if not isfile(xpkg):
        xpkg = None
    xdir = join(pdir, dist)
    if not (isdir(xdir) and
            isfile(join(xdir, 'info', 'files')) and
            isfile(join(xdir, 'info', 'index.json'))):
        xdir = None
    if not (xpkg or xdir):
        return
    if url:
        url = url

    # make dist
    schannel = Channel(url).canonical_name
    prefix = '' if schannel == DEFAULTS else schannel + '::'
    xkey = xpkg or (xdir + '.tar.bz2')
    fname_table_[xkey] = fname_table_[path_to_url(xkey)] = prefix
    fkey = prefix + dist

    dist = Dist(fkey)

    rec = package_cache_.get(dist)
    if rec is None:
        rec = package_cache_[dist] = dict(files=[], dirs=[], urls=[])
    if url and url not in rec['urls']:
        rec['urls'].append(url)
    if xpkg and xpkg not in rec['files']:
        rec['files'].append(xpkg)
    if xdir and xdir not in rec['dirs']:
        rec['dirs'].append(xdir)
    if urlstxt:
        try:
            with open(join(pdir, 'urls.txt'), 'a') as fa:
                fa.write('%s\n' % url)
        except IOError:
            pass


def package_cache():
    """
    Initializes the package cache. Each entry in the package cache
    dictionary contains three lists:
    - urls: the URLs used to refer to that package
    - files: the full pathnames to fetched copies of that package
    - dirs: the full pathnames to extracted copies of that package
    Nominally there should be no more than one entry in each list, but
    in theory this can handle the presence of multiple copies.
    """
    if package_cache_:
        return package_cache_
    # Stops recursion
    package_cache_['@'] = None

    for pdir in context.pkgs_dirs:
        try:
            data = open(join(pdir, 'urls.txt')).read()
            for url in data.split()[::-1]:
                if '/' in url:
                    add_cached_package(pdir, url)
        except IOError:
            pass
        if isdir(pdir):
            for fn in os.listdir(pdir):
                add_cached_package(pdir, fn)
    del package_cache_['@']
    return package_cache_


def cached_url(url):
    package_cache()
    return fname_table_.get(url)


def find_new_location(dist):
    """
    Determines the download location for the given package, and the name
    of a package, if any, that must be removed to make room. If the
    given package is already in the cache, it returns its current location,
    under the assumption that it will be overwritten. If the conflict
    value is None, that means there is no other package with that same
    name present in the cache (e.g., no collision).
    """
    rec = package_cache().get(dist)
    if rec:
        return dirname((rec['files'] or rec['dirs'])[0]), None
    # Look for a location with no conflicts
    # On the second pass, just pick the first location
    for p in range(2):
        for pkg_dir in context.pkgs_dirs:
            pkg_path = join(pkg_dir, dist.to_filename())
            prefix = fname_table_.get(pkg_path)
            if p or prefix is None:
                return pkg_dir, prefix + dist.dist_name if p else None


# ------- package cache ----- fetched

def fetched():
    """
    Returns the (set of canonical names) of all fetched packages
    """
    return set(dist for dist, rec in package_cache().items() if rec['files'])


def is_fetched(dist):
    """
    Returns the full path of the fetched package, or None if it is not in the cache.
    """
    for fn in package_cache().get(dist, {}).get('files', ()):
        return fn


def rm_fetched(dist):
    """
    Checks to see if the requested package is in the cache; and if so, it removes both
    the package itself and its extracted contents.
    """
    rec = package_cache().get(dist)
    if rec is None:
        return
    for fname in rec['files']:
        del fname_table_[fname]
        del fname_table_[path_to_url(fname)]
        with FileLock(fname):
            rm_rf(fname)
            if exists(fname):
                log.warn("File not removed during RM_FETCHED instruction: %s", fname)
    for fname in rec['dirs']:
        with FileLock(fname):
            rm_rf(fname)
            if exists(fname):
                log.warn("Directory not removed during RM_FETCHED instruction: %s", fname)
    del package_cache_[dist]


# ------- package cache ----- extracted

def extracted():
    """
    return the (set of canonical names) of all extracted packages
    """
    return set(dist for dist, rec in package_cache().items() if rec['dirs'])


def is_extracted(dist):
    """
    returns the full path of the extracted data for the requested package,
    or None if that package is not extracted.
    """
    for fn in package_cache().get(dist, {}).get('dirs', ()):
        return fn


def rm_extracted(dist):
    """
    Removes any extracted versions of the given package found in the cache.
    """
    rec = package_cache().get(dist)
    if rec is None:
        return
    for fname in rec['dirs']:
        with FileLock(fname):
            rm_rf(fname)
            if exists(fname):
                log.warn("Directory not removed during RM_EXTRACTED instruction: %s", fname)
    if rec['files']:
        rec['dirs'] = []
    else:
        del package_cache_[dist]


def extract(dist):
    """
    Extract a package, i.e. make a package available for linkage. We assume
    that the compressed package is located in the packages directory.
    """
    rec = package_cache()[dist]
    url = rec['urls'][0]
    fname = rec['files'][0]
    assert url and fname
    pkgs_dir = dirname(fname)
    path = fname[:-8]
    with FileLock(path):
        temp_path = path + '.tmp'
        rm_rf(temp_path)
        with tarfile.open(fname) as t:
            t.extractall(path=temp_path)
        rm_rf(path)
        exp_backoff_fn(os.rename, temp_path, path)
        if sys.platform.startswith('linux') and os.getuid() == 0:
            # When extracting as root, tarfile will by restore ownership
            # of extracted files.  However, we want root to be the owner
            # (our implementation of --no-same-owner).
            for root, dirs, files in os.walk(path):
                for fn in files:
                    p = join(root, fn)
                    os.lchown(p, 0, 0)
        add_cached_package(pkgs_dir, url, overwrite=True)


def read_url(dist):
    res = package_cache().get(dist, {}).get('urls', (None,))
    return res[0] if res else None


def fetch_pkg(info, dst_dir=None, session=None):
    '''
    fetch a package given by `info` and store it into `dst_dir`
    '''

    session = session or CondaSession()

    fn = info['fn']

    url = info.get('url') or info['channel'] + '/' + fn
    url = maybe_add_auth(url, info.get('auth'))
    log.debug("url=%r" % url)

    if dst_dir is None:
        dst_dir = find_new_location(Dist(fn))[0]
    path = join(dst_dir, fn)

    download(url, path, session=session, md5=info['md5'], urlstxt=True)
    if info.get('sig'):
        from ..signature import verify

        fn2 = fn + '.sig'
        url = (info['channel'] if info['sig'] == '.' else
               info['sig'].rstrip('/')) + '/' + fn2
        log.debug("signature url=%r" % url)
        download(url, join(dst_dir, fn2), session=session)
        try:
            if verify(path):
                return
        except CondaSignatureError:
            raise

        raise CondaSignatureError("Error: Signature for '%s' is invalid." % (basename(path)))


def download(url, dst_path, session=None, md5=None, urlstxt=False, retries=None):
    assert "::" not in str(dst_path), str(dst_path)
    if not offline_keep(url):
        raise RuntimeError("Cannot download in offline mode: %s" % (url,))

    pp = dst_path + '.part'
    dst_dir = dirname(dst_path)
    session = session or CondaSession()

    if not context.ssl_verify:
        try:
            from requests.packages.urllib3.connectionpool import InsecureRequestWarning
        except ImportError:
            pass
        else:
            warnings.simplefilter('ignore', InsecureRequestWarning)

    if retries is None:
        retries = RETRIES

    with FileLock(dst_path):
        rm_rf(dst_path)
        try:
            resp = session.get(url, stream=True, proxies=session.proxies, timeout=(3.05, 27))
            resp.raise_for_status()
        except requests.exceptions.HTTPError as e:
            msg = "HTTPError: %s: %s\n" % (e, url)
            log.debug(msg)
            raise CondaRuntimeError(msg)

        except requests.exceptions.ConnectionError as e:
            msg = "Connection error: %s: %s\n" % (e, url)
            stderrlog.info('Could not connect to %s\n' % url)
            log.debug(msg)
            raise CondaRuntimeError(msg)

        except IOError as e:
            raise CondaRuntimeError("Could not open '%s': %s" % (url, e))

        size = resp.headers.get('Content-Length')
        if size:
            size = int(size)
            fn = basename(dst_path)
            getLogger('fetch.start').info((fn[:14], size))

        if md5:
            h = hashlib.new('md5')
        try:
            with open(pp, 'wb') as fo:
                index = 0
                for chunk in resp.iter_content(2**14):
                    index += len(chunk)
                    try:
                        fo.write(chunk)
                    except IOError:
                        raise CondaRuntimeError("Failed to write to %r." % pp)

                    if md5:
                        h.update(chunk)

                    if size and 0 <= index <= size:
                        getLogger('fetch.update').info(index)

        except IOError as e:
            if e.errno == 104 and retries:  # Connection reset by pee
                # try again
                log.debug("%s, trying again" % e)
                return download(url, dst_path, session=session, md5=md5,
                                urlstxt=urlstxt, retries=retries - 1)
            raise CondaRuntimeError("Could not open %r for writing (%s)." % (pp, e))

        if size:
            getLogger('fetch.stop').info(None)

        if md5 and h.hexdigest() != md5:
            if retries:
                # try again
                log.debug("MD5 sums mismatch for download: %s (%s != %s), "
                          "trying again" % (url, h.hexdigest(), md5))
                return download(url, dst_path, session=session, md5=md5,
                                urlstxt=urlstxt, retries=retries - 1)
            raise MD5MismatchError("MD5 sums mismatch for download: %s (%s != %s)"
                                   % (url, h.hexdigest(), md5))

        try:
            exp_backoff_fn(os.rename, pp, dst_path)
        except OSError as e:
            raise CondaRuntimeError("Could not rename %r to %r: %r" %
                                    (pp, dst_path, e))

        if urlstxt:
            add_cached_package(dst_dir, url, overwrite=True, urlstxt=True)
