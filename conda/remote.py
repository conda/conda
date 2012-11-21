# (c) 2012 Continuum Analytics, Inc. / http://continuum.io
# All Rights Reserved
#
# conda is distributed under the terms of the BSD 3-clause license.
# Consult LICENSE.txt or http://opensource.org/licenses/BSD-3-Clause.
''' The remote module provides functions for interfacing with remote Anaconda
repositories.

'''

import os
import hashlib
import urllib2
import logging
from os.path import join

from config import config


log = logging.getLogger(__name__)


def fetch_file(fn, md5=None, size=None, progress=None):
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
    if size is None:
        length = int(fi.headers["Content-Length"])
    else:
        length = size

    if progress:
        progress.widgets[0] = fn
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
