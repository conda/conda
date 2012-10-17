import os
import hashlib
import urllib2
import logging
from os.path import join

from config import config


log = logging.getLogger(__name__)


def ls_files(file_pat=re.compile(r'(([\w\.-]+)+\.tar\.bz2)')):
    '''
    Return a set of all files for the current architecture from all known repositories.
    '''
    res = set()
    conf = config()
    for url in conf.repo_package_urls:
        log.debug("fetching files list [%s] ..." % url)
        try:
            fi = urllib2.urlopen(url)
            for match in file_pat.finditer(fi.read()):
                res.add(match.group(0))
            fi.close()
            log.debug("    ...succeeded.")
        except:
            log.debug("    ...failed.")
    return res


def file_locations(file_pat=re.compile(r'(([\w\.-]+)+\.tar\.bz2)')):
    '''
    Return a dictionary of all files for the current architecture from all known
    repositories, together with their repository location.
    '''
    res = {}
    conf = config()
    for url in conf.repo_package_urls:
        logging.debug("fetching files list [%s] ..." % url)
        try:
            fi = urllib2.urlopen(url)
            for match in file_pat.finditer(fi.read()):
                fn = match.group()
                if not res.has_key(fn): res[fn] = url
            fi.close()
            log.debug("    ...succeeded.")
        except:
            log.debug("    ...failed.")

    return res


def fetch_file(fn, md5=None, progress=None):
    '''
    Search all known repositories (in order) for the specified file and
    download it, optionally checking an md5 checksum.
    '''
    conf = config()
    path = join(conf.packages_dir, fn)
    pp = path + '.part'
    fi = None
    for url in conf.repo_package_urls:
        try:
            fi = urllib2.urlopen(url + fn)
            log.debug("fetching: %s [%s]" % (fn, url))
            break
        except:
            pass
    if not fi:
        raise RuntimeError(
            "Could not locate file '%s' on any repository" % fn
        )
    n = 0
    h = hashlib.new('md5')
    length = int(fi.headers["Content-Length"])

    if progress:
        progress.widgets.insert(0, fn)
        progress.maxval = length
        progress.start()

    with open(pp, 'wb') as fo:
        while True:
            chunk = fi.read(16384)
            if not chunk:
                break
            fo.write(chunk)
            if md5:
                h.update(chunk)
            n += len(chunk)
            if progress: progress.update(n)
    fi.close()
    if progress: progress.finish()
    if md5 and h.hexdigest() != md5:
        raise ValueError("MD5 sums mismatch for: %s" % fn)
    os.rename(pp, path)
    return url
