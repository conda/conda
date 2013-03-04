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
from install import available
from remote import fetch_repodata
from package_index import PackageIndex


log = logging.getLogger(__name__)


class Anaconda(Config):
    ''' Provides configuration for an Anaconda installation, including the appropriate package index.

    Attributes
    ----------
    available_packages : set of Package objects
    default_environment : Environment object
    environments : list of Environment objects
    index : PackageIndex object
    root_environment : Environment object

    '''
    __slots__ = ['_index', '_available']

    def __init__(self, **kw):
        super(Anaconda, self).__init__(**kw)

        self._index = PackageIndex(self._fetch_index())

        # compute on demand
        self._available = None

    @property
    def index(self):
        ''' Anaconda package index '''
        return self._index

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

    @property
    def available_packages(self):
        ''' All :ref:`locally available <locally_available>` packages '''
        if not self._available:
            self._available = set()
            canonical_names = available(self.packages_dir)
            for name in canonical_names:
                try:
                    self._available.add(self.index.lookup_from_canonical_name(name))
                except KeyError:
                    log.debug("unknown available package '%s'" % name)
        return self._available

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
            repodata = fetch_repodata(url)
            new_index = repodata['packages']
            for pkg_info in new_index.itervalues():
                pkg_info['channel'] = url
            index.update(new_index)

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
