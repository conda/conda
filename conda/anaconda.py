# (c) 2012 Continuum Analytics, Inc. / http://continuum.io
# All Rights Reserved
#
# conda is distributed under the terms of the BSD 3-clause license.
# Consult LICENSE.txt or http://opensource.org/licenses/BSD-3-Clause.
''' The anaconda module provides the `anaconda` class, which provides configuration
information about an Anaconda installation, including the Anaconda package index.

'''

from bz2 import decompress
from os import listdir
from os.path import exists, join
from urllib2 import urlopen
import json
import logging

from config import config
from package_index import package_index


log = logging.getLogger(__name__)


class anaconda(config):
    ''' Provides configuration for an Anaconda installation, including the appropriate package index.

    Attributes
    ----------
    index

    '''
    __slots__ = ['_index', '_local_index_only']

    def __init__(self):
        super(anaconda, self).__init__()

        index = self._build_local_index()
        try:
            index.update(self._fetch_index())
            self._local_index_only = False
        except RuntimeError:
            self._local_index_only = True

        self._index = package_index(index)

    @property
    def index(self):
        ''' Anaconda package index '''
        return self._index

    @property
    def local_index_only(self):
        ''' Whether the package index contains only local information '''
        return self._local_index_only

    def __repr__(self):
        return 'anaconda()'

    def _fetch_index(self):
        index = {}
        for url in reversed(self.repo_package_urls):
            try:
                fi = urlopen(url + 'repodata.json.bz2')
                log.debug("fetched: repodata.json.bz2 [%s] ..." % url)
                repodata = json.loads(decompress(fi.read()))
            except:
                try:
                    fi = urlopen(url + 'repodata.json')
                    log.debug("fetched: repodata.json [%s] ..." % url)
                    repodata = json.loads(fi.read())
                except:
                    log.debug("failed to fetch repo data at url %s" % url)
                    continue
            new_index = repodata['packages']
            for pkg_info in new_index.itervalues():
                pkg_info['location'] = url
            index.update(new_index)
            fi.close()
            log.debug("    ...succeeded.")

        if not index:
            raise RuntimeError(
                'Could not locate index files on any repository'
            )
        return index

    def _build_local_index(self):
        try:
            log.debug('building index from local packages repository at'
                      ' self.packages_dir')
            index = {}
            for fn in listdir(self.packages_dir):
                if exists(join(self.packages_dir, fn, 'info', 'index.json')):
                    index[fn+'.tar.bz2'] = json.load(
                        open(join(self.packages_dir, fn, 'info', 'index.json'))
                    )
            return index
        except IOError as e:
            raise RuntimeError('Could not build index from local package '
                               'repository, reason: %s' % e)
