# (c) 2012 Continuum Analytics, Inc. / http://continuum.io
# All Rights Reserved
#
# conda is distributed under the terms of the BSD 3-clause license.
# Consult LICENSE.txt or http://opensource.org/licenses/BSD-3-Clause.
''' The config module provides the `config` class, which exposes all the
configuration information about an Anaconda installation that does not require
the Anaconda package index.

'''


from os import getenv, listdir
from os.path import abspath, exists, expanduser, isdir, join
import logging
import platform
import sys

from conda import __version__
from environment import environment
from install import available


log = logging.getLogger(__name__)


CIO_DEFAULT_REPOS = [
    'http://repo.continuum.io/pkgs'
]

INFO_STRING = '''
               target : %s
             platform : %s
conda command version : %s
       root directory : %s
   packages directory : %s
      repository URLS : %s
environment locations : %s
'''

VERSION = __version__

ROOT_DIR = sys.prefix

ROOT = ROOT_DIR # This is deprecated, do not use in new code

PACKAGES_DIR = join(ROOT_DIR, 'pkgs')


DEFAULT_PYTHON_SPEC='python=2.7'
if sys.platform == 'win32':
    DEFAULT_NUMPY_SPEC='numpy=1.6'
else:
    DEFAULT_NUMPY_SPEC='numpy=1.7'

def _load_condarc(path):
    try:
        import yaml
    except ImportError:
        log.warn("yaml module missing, cannot read .condarc files")
        return None
    try:
        rc = yaml.load(open(path))
    except IOError:
        return None
    log.debug("loaded: %s" % path)
    return rc


class config(object):
    ''' The config object collects a variety of configuration about an Anaconda installation.

    Attributes
    ----------
    conda_version
    default_environment
    environments
    locations
    packages_dir
    platform
    repo_base_urls
    repo_package_urls
    root_dir
    system_location
    target
    user_locations

    '''

    __slots__ = ['_rc']

    def __init__(self):
        self._rc = None

        # try to load .condarc file from users home directory
        home = getenv('USERPROFILE') or getenv('HOME')
        self._rc = _load_condarc(join(home, '.condarc'))

        if not self._rc:
            self._rc = _load_condarc(join(ROOT_DIR, '.condarc'))

    @property
    def conda_version(self):
        ''' Current version of the conda command '''
        return VERSION

    @property
    def target(self):
        ''' Current build target of this Anaconda installation

        The possible values are:
            ``ce``
                Community Edition
            ``pro``
                Anaconda pro
            ``unknown``
                non-Anaconda python
        '''
        env_target = getenv('CIO_TARGET')
        if env_target:
            return env_target

        if 'AnacondaCE' in sys.version:
            return 'ce'
        elif 'Anaconda' in sys.version:
            return 'pro'
        else:
            return 'unknown'

    @property
    def platform(self):
        '''
        The current platform of this Anaconda installation

        Platorm values are expressed as `system`-`bits`.

        The possible system values are:
            - ``win``
            - ``osx``
            - ``linux``
        '''
        sys_map = {'linux2': 'linux', 'darwin': 'osx', 'win32': 'win'}
        bits = int(platform.architecture()[0][:2])
        system = sys_map.get(sys.platform, 'unknown')
        return '%s-%d' % (system, bits)

    @property
    def root_dir(self):
        ''' Root directory for this Anaconda installation '''
        return ROOT_DIR

    @property
    def packages_dir(self):
        ''' Packages directory for this Anaconda installation '''
        return PACKAGES_DIR

    @property
    def system_location(self):
        ''' Default system :ref:`location <location>` for new :ref:`Anaconda environments <environment>` '''
        return join(ROOT_DIR, 'envs')

    @property
    def user_locations(self):
        ''' Additional user supplied :ref:`locations <location>` for new :ref:`Anaconda environments <environment>` '''
        locations = []
        if self._rc:
            locations.extend(self._rc.get('locations', []))
        return sorted(abspath(expanduser(location)) for location in locations)

    @property
    def locations(self):
        ''' All :ref:`locations <location>`, system and user '''
        return sorted(self.user_locations + [self.system_location])

    @property
    def default_environment(self):
        ''' Default :ref:`Anaconda environment <environment>` '''
        return environment(self, ROOT_DIR)

    @property
    def environments(self):
        ''' All known Anaconda environments

        :ref:`Anaconda environments <environment>` are serached for in the directories specified by `config.locations`.
        Environments located elswhere are unknown to Anaconda.
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
                        envs.append(environment(self, prefix))
                    except RuntimeError as e:
                        log.info('%s' % e)
        envs.append(self.default_environment)
        return sorted(envs)

    @property
    def repo_base_urls(self):
        ''' Base URLS of :ref:`Anaconda repositories <repository>` '''
        if getenv('CIO_TEST') == "2":
            return ['http://filer/test-pkgs', 'http://filer/pkgs']
        elif getenv('CIO_TEST') == "1":
            return ['http://filer/pkgs']
        elif self._rc:
            return self._rc['repositories']
        else:
            return CIO_DEFAULT_REPOS

    @property
    def repo_package_urls(self):
        ''' Platorm-specific package URLS of :ref:`Anaconda repositories <repository>` '''
        return [
            '%s/%s/' % (url, self.platform) for url in self.repo_base_urls
        ]

    @property
    def available_packages(self):
        ''' All :ref:`locally available <locally_available>` packages '''
        res = set()
        canonical_names = available(self.packages_dir)
        for name in canonical_names:
            try:
                res.add(self.index.lookup_from_canonical_name(name))
            except KeyError:
                log.debug("unknown available package '%s'" % name)
        return res

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
            return environment(self, prefix)

    def __str__(self):
        return INFO_STRING % (
            self.target,
            self.platform,
            self.conda_version,
            self.root_dir,
            self.packages_dir,
            self.repo_package_urls,
            self.locations,
        )

    def __repr__(self):
        return 'config()'
