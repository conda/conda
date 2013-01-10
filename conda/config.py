# (c) 2012 Continuum Analytics, Inc. / http://continuum.io
# All Rights Reserved
#
# conda is distributed under the terms of the BSD 3-clause license.
# Consult LICENSE.txt or http://opensource.org/licenses/BSD-3-Clause.
''' The config module provides the `config` class, which exposes all the
configuration information about an Anaconda installation that does not require
the Anaconda package index.

'''
from datetime import datetime
import logging
import os
from os.path import abspath, exists, expanduser, isdir, join
import platform
import sys

from conda import __version__


log = logging.getLogger(__name__)


CIO_DEFAULT_CHANNELS = [
    'http://repo.continuum.io/pkgs/free'
]

CIO_PRO_CHANNEL = 'http://repo.continuum.io/pkgs/pro'

VERSION = __version__

ROOT_DIR = sys.prefix

ROOT = ROOT_DIR # This is deprecated, do not use in new code

PACKAGES_DIR = join(ROOT_DIR, 'pkgs')
ENVS_DIR = join(ROOT_DIR, 'envs')

_default_env = os.getenv('CONDA_DEFAULT_ENV')
if not _default_env:
    DEFAULT_ENV_PREFIX = ROOT_DIR
elif os.sep in _default_env:
    DEFAULT_ENV_PREFIX = abspath(_default_env)
else:
    DEFAULT_ENV_PREFIX = join(ENVS_DIR, _default_env)

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


class Config(object):
    ''' The config object collects a variety of configurations about an Anaconda installation.

    Attributes
    ----------
    conda_version
    root_environment
    default_environment
    environments
    locations
    packages_dir
    platform
    channel_base_urls
    channel_urls
    root_dir
    system_location
    user_locations

    '''

    __slots__ = ['_rc']

    def __init__(self, first_channel=None):
        self._rc = None

        # try to load .condarc file from users home directory
        home = os.getenv('USERPROFILE') or os.getenv('HOME')
        self._rc = _load_condarc(join(home, '.condarc'))

        if not self._rc:
            self._rc = {'channels': CIO_DEFAULT_CHANNELS}

        elif not self._rc.has_key('channels'):
            log.info("old condarc, missing 'channels' key, using default channels: %s"  % CIO_DEFAULT_CHANNELS)
            self._rc['channels']  = CIO_DEFAULT_CHANNELS

        if 'Anaconda ' in sys.version:
            exp_date = None
            try:
                import _license
                exp_date = _license.get_end_date()
            except:
                pass
            if exp_date and datetime.today() <= datetime.strptime(exp_date, '%Y-%m-%d'):
                self._rc['channels'].insert(0, CIO_PRO_CHANNEL)

        if first_channel:
            self._rc['channels'].insert(0, first_channel)

    @property
    def conda_version(self):
        ''' Current version of the conda command '''
        return VERSION

    @property
    def platform(self):
        '''
        The current platform of this Anaconda installation

        Platform values are expressed as `system`-`bits`.

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
        return ENVS_DIR

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
    def root_environment(self):
        ''' Root :ref:`Anaconda environment <environment>` '''
        from environment import Environment
        return Environment(self, ROOT_DIR)

    @property
    def default_environment(self):
        ''' Default :ref:`Anaconda environment <environment>` '''
        from environment import Environment
        return Environment(self, DEFAULT_ENV_PREFIX)

    @property
    def environments(self):
        ''' All known Anaconda environments

        :ref:`Anaconda environments <environment>` are searched for in the directories specified by `config.locations`.
        Environments located elsewhere are unknown to Anaconda.
        '''
        from environment import Environment
        envs = []
        for location in self.locations:
            if not exists(location):
                log.warning("location '%s' does not exist" % location)
                continue
            for fn in os.listdir(location):
                prefix = join(location, fn)
                if isdir(prefix):
                    try:
                        envs.append(Environment(self, prefix))
                    except RuntimeError as e:
                        log.info('%s' % e)
        envs.append(self.default_environment)
        return sorted(envs)

    @property
    def channel_base_urls(self):
        ''' Base URLS of :ref:`Anaconda channels <channel>` '''
        if os.getenv('CIO_TEST') == "1":
            return ['http://filer/pkgs/pro', 'http://filer/pkgs/free']
        else:
            return self._rc['channels']

    @property
    def channel_urls(self):
        ''' Platform-specific package URLS of :ref:`Anaconda channels <channel>` '''
        return [
            '%s/%s/' % (url, self.platform) for url in self.channel_base_urls
        ]

    @property
    def available_packages(self):
        ''' All :ref:`locally available <locally_available>` packages '''
        from install import available
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
            from environment import Environment
            return Environment(self, prefix)

    def __str__(self):
        return '''
             platform : %s
conda command version : %s
       root directory : %s
       default prefix : %s
         channel URLS : %s
environment locations : %s
'''  % (
            self.platform,
            self.conda_version,
            ROOT_DIR,
            DEFAULT_ENV_PREFIX,
            self.channel_urls,
            self.locations,
        )

    def __repr__(self):
        return 'config()'
