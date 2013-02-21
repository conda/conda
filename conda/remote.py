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

from config import PACKAGES_DIR


log = logging.getLogger(__name__)


def fetch_file(fn, channels, md5=None, size=None, progress=None, pkgs_dir=PACKAGES_DIR):
    '''
    Search all known channels (in order) for the specified file and
    download it, optionally checking an md5 checksum.
    '''
    path = join(pkgs_dir, fn)
    pp = path + '.part'
    fi = None
    for url in channels:
        try:
            fi = urllib2.urlopen(url + fn)
            log.debug("fetching: %s [%s]" % (fn, url))
            break
        except IOError:
            pass
    if not fi:
        raise RuntimeError(
            "Could not locate file '%s' on any repository" % fn
        )
    fi.close()

    for x in range(5):
        try:
            fi = urllib2.urlopen(url + fn, timeout=60)
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
                raise RuntimeError("MD5 sums mismatch for download: %s" % fn)
            os.rename(pp, path)
            return url
        except IOError:
            log.debug('download failed try: %d' % x)
