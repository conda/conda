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
from os.path import exists, isdir, join
from urllib2 import urlopen
import json
import logging

from config import Config, DEFAULT_ENV_PREFIX, ROOT_DIR
from environment import Environment
from package_index import PackageIndex


log = logging.getLogger(__name__)


class Anaconda(Config):
    ''' Provides configuration for an Anaconda installation, including the appropriate package index.

    Attributes
    ----------
    index

    '''
    __slots__ = ['_index', '_local_index_only']

    def __init__(self, **kw):
        super(Anaconda, self).__init__(**kw)

        try:
            remote_index = self._fetch_index()
            self._index = PackageIndex(remote_index)
            self._local_index_only = False
        except RuntimeError:
            local_index = self._build_local_index()
            self._index = PackageIndex(local_index)
            self._local_index_only = True

    @property
    def index(self):
        ''' Anaconda package index '''
        return self._index

    @property
    def local_index_only(self):
        ''' Whether the package index contains only local information '''
        return self._local_index_only

    @property
    def root_environment(self):
        ''' Root :ref:`Anaconda environment <environment>` '''
        return Environment(self, ROOT_DIR)

    @property
    def default_environment(self):
        ''' Default :ref:`Anaconda environment <environment>` '''
        return Environment(self, DEFAULT_ENV_PREFIX)


    @property
    def environments(self):
        ''' All known Anaconda environments

        :ref:`Anaconda environments <environment>` are searched for in the directories specified by `config.locations`.
        Environments located elsewhere are unknown to Anaconda.
        '''
        envs = []
        for location in self.locations:
            if not exists(location):
                log.warning("location '%s' does not exist" % location)
                continue
            for fn in listdir(location):
                prefix = join(location, fn)
                if isdir(prefix):
                    try:
                        envs.append(Environment(self, prefix))
                    except RuntimeError as e:
                        log.info('%s' % e)
        envs.append(self.default_environment)
        return sorted(envs)

    def lookup_environment(self, prefix):
        '''
        Return an environment object for the :ref:`Anaconda environment <environment>` located at `prefix`.

        Parameters
        ----------
        prefix : str
            full path to find Anaconda environment

        Returns
        -------
        env : environment
            environment object for Anaconda environment located at `prefix`

        '''
        envs = dict((env.prefix, env) for env in self.environments)
        try:
            return envs[prefix]
        except:
            log.debug('creating environment for prefix: %s' % prefix)
            return Environment(self, prefix)

    def __repr__(self):
        return 'anaconda()'

    def _fetch_index(self):
        index = {}
        for url in reversed(self.channel_urls):
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
                pkg_info['channel'] = url
            index.update(new_index)
            fi.close()
            log.debug("    ...succeeded.")

        if not index:
            raise RuntimeError(
                'Could not locate index files on any channel'
            )
        return index

    def _build_local_index(self):
        try:
            log.debug('building index from local packages at self.packages_dir')
            index = {}
            for fn in listdir(self.packages_dir):
                if exists(join(self.packages_dir, fn, 'info', 'index.json')):
                    index[fn+'.tar.bz2'] = json.load(
                        open(join(self.packages_dir, fn, 'info', 'index.json'))
                    )
            return index
        except IOError as e:
            raise RuntimeError('Could not build index from local packages, reason: %s' % e)
