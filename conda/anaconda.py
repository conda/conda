''' The anaconda modude provides the `anaconda` class, which provides configuration information about an
Anaconda installation, including the Anaconda package index.

'''

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
    __slots__ = ['_index']

    def __init__(self):
        super(anaconda, self).__init__()

        try:
            self._index = package_index(self._fetch_index())
        except RuntimeError:
            self._index = package_index(self._build_local_index())

    @property
    def index(self):
        ''' Anaconda package index '''
        return self._index

    def __repr__(self):
        return 'anaconda()'

    def _fetch_index(self):
        index = {}
        for url in reversed(self.repo_package_urls):
            log.debug("fetching: repodata.json [%s] ..." % url)
            try:
                fi = urlopen(url + 'repodata.json')
            except:  # TODO better exception spec
                log.debug("    ...failed.")
                continue
            repodata = json.loads(fi.read())
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
                               'respitory, reason: %s' % e)
