# (c) 2012-2013 Continuum Analytics, Inc. / http://continuum.io
# All Rights Reserved
#
# conda is distributed under the terms of the BSD 3-clause license.
# Consult LICENSE.txt or http://opensource.org/licenses/BSD-3-Clause.

import os
import bz2
import json
import hashlib
import urllib2
from logging import getLogger
from os.path import join

import config
from utils import memoized


log = getLogger(__name__)
retries = 3


def fetch_repodata(url):
    for x in range(retries):
        for fn in 'repodata.json.bz2', 'repodata.json':
            try:
                fi = urllib2.urlopen(url + fn)
                log.debug("fetched: %s [%s] ..." % (fn, url))
                data = fi.read()
                fi.close()
                if fn.endswith('.bz2'):
                    data = bz2.decompress(data)
                return json.loads(data)

            except IOError:
                log.debug('download failed try: %d' % x)

    raise RuntimeError("failed to fetch repodata from %r" % url)


@memoized
def fetch_index(channel_urls):
    index = {}
    for url in reversed(channel_urls):
        repodata = fetch_repodata(url)
        new_index = repodata['packages']
        for info in new_index.itervalues():
            info['channel'] = url
        index.update(new_index)
    return index


def fetch_pkg(info, dst_dir=config.pkgs_dir):
    '''
    fetch a package `fn` from `url` and store it into `dst_dir`
    '''
    fn = '%(name)s-%(version)s-%(build)s.tar.bz2' % info
    url = info['channel'] + fn
    path = join(dst_dir, fn)
    pp = path + '.part'

    for x in range(retries):
        try:
            fi = urllib2.urlopen(url)
        except IOError:
            log.debug("Attempt %d failed at urlopen" % x)
            continue
        log.debug("Fetching: %s" % url)
        n = 0
        h = hashlib.new('md5')
        getLogger('progress.start').info({'filename': fn,
                                          'maxval': info['size']})
        need_retry = False
        try:
            fo = open(pp, 'wb')
        except IOError:
            raise RuntimeError("Could not open %r for writing.  "
                         "Permissions problem or missing directory?" % pp)
        while True:
            try:
                chunk = fi.read(16384)
            except IOError:
                need_retry = True
                break
            if not chunk:
                break
            try:
                fo.write(chunk)
            except IOError:
                raise RuntimeError("Failed to write to %r." % pp)
            h.update(chunk)
            n += len(chunk)
            getLogger('progress.update').info(n)

        fo.close()
        if need_retry:
            continue

        fi.close()
        getLogger('progress.stop').info(None)
        if h.hexdigest() != info['md5']:
            raise RuntimeError("MD5 sums mismatch for download: %s" % fn)
        try:
            os.rename(pp, path)
        except OSError:
            raise RuntimeError("Could not rename %r to %r." % (pp, path))
        return

    raise RuntimeError("Could not locate file '%s' on any repository" % fn)
