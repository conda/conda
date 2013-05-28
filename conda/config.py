# (c) 2012-2013 Continuum Analytics, Inc. / http://continuum.io
# All Rights Reserved
#
# conda is distributed under the terms of the BSD 3-clause license.
# Consult LICENSE.txt or http://opensource.org/licenses/BSD-3-Clause.

import os
import sys
from platform import machine
from os.path import abspath, exists, expanduser, isfile, isdir, join



default_python = '2.7'
default_numpy = '1.7'

# ----- constant paths -----

root_dir = sys.prefix
pkgs_dir = join(root_dir, 'pkgs')
envs_dir = join(root_dir, 'envs')

# ----- default environment path -----

_default_env = os.getenv('CONDA_DEFAULT_ENV')
if not _default_env:
    DEFAULT_ENV_PREFIX = root_dir
elif os.sep in _default_env:
    DEFAULT_ENV_PREFIX = abspath(_default_env)
else:
    DEFAULT_ENV_PREFIX = join(envs_dir, _default_env)

# ----- operating system and architecture -----

_sys_map = {'linux2': 'linux', 'darwin': 'osx', 'win32': 'win'}
platform = _sys_map.get(sys.platform, 'unknown')
bits = 8 * tuple.__itemsize__

if platform == 'linux' and machine() == 'armv6l':
    subdir = 'linux-armv6l'
    arch_name = 'armv6l'
else:
    subdir = '%s-%d' % (platform, bits)
    arch_name = {64: 'x86_64', 32: 'x86'}[bits]

# ----- rc file -----

def get_rc_path():
    for path in [abspath(expanduser('~/.condarc')),
                 join(sys.prefix, '.condarc')]:
        if isfile(path):
            return path
    return None

rc_path = get_rc_path()

def load_condarc(path):
    import yaml

    return yaml.load(open(path))

# ----- channels -----

def get_channel_urls():
    if os.getenv('CIO_TEST'):
        base_urls = ['http://filer/pkgs/pro', 'http://filer/pkgs/free']
        if os.getenv('CIO_TEST') == '2':
            base_urls.insert(0, 'http://filer/test-pkgs')

    elif rc_path is None:
        base_urls = ['http://repo.continuum.io/pkgs/free',
                     'http://repo.continuum.io/pkgs/pro']

    else:
        rc = load_condarc(rc_path)
        if 'channels' not in rc:
            sys.exit("Error: config file '%s' is missing channels" % rc_path)
        base_urls = [url.rstrip('/') for url in rc['channels']]

    return ['%s/%s/' % (url, subdir) for url in base_urls]



# ========================================================================

import logging

log = logging.getLogger(__name__)

CIO_DEFAULT_CHANNELS = [
    'http://repo.continuum.io/pkgs/free',
    'http://repo.continuum.io/pkgs/pro',
]

DEFAULT_PYTHON_SPEC = 'python=2.7'
DEFAULT_NUMPY_SPEC = 'numpy=1.7'

ROOT_DIR = sys.prefix

def _get_rc_path():
    for path in [abspath(expanduser('~/.condarc')),
                 join(sys.prefix, '.condarc')]:
        if isfile(path):
            return path
    return None

RC_PATH = _get_rc_path()

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
    if 'channels' in rc:
        rc['channels'] = [url.rstrip('/') for url in rc['channels']]
    else:
        log.warn("missing 'channels' key in %r"  % path)
    return rc


class Config(object):
    ''' The config object collects a variety of configurations about a conda installation.

    Attributes
    ----------
    channel_base_urls : list of str
    channel_urls : list of str
    environment_paths : list of str
    locations : list of str
    packages_dir : str
    platform : str
    user_locations : list of str

    '''

    __slots__ = ['_rc']

    def __init__(self, first_channel=None):
        self._rc = None

        if RC_PATH is None:
            self._rc = {'channels': CIO_DEFAULT_CHANNELS}
        else:
            self._rc = _load_condarc(RC_PATH)

        if first_channel:
            self._rc['channels'].insert(0, first_channel)

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
        return subdir

    @property
    def packages_dir(self):
        ''' Packages directory for this Anaconda installation '''
        return pkgs_dir

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
        return sorted(self.user_locations + [envs_dir])

    @property
    def channel_base_urls(self):
        ''' Base URLS of :ref:`Anaconda channels <channel>` '''
        if os.getenv('CIO_TEST'):
            res = ['http://filer/pkgs/pro', 'http://filer/pkgs/free']
            if os.getenv('CIO_TEST') == "2":
                res.insert(0, 'http://filer/test-pkgs')
            return res
        else:
            return self._rc['channels']

    @property
    def channel_urls(self):
        ''' Platform-specific package URLS of :ref:`Anaconda channels <channel>` '''
        return [
            '%s/%s/' % (url, self.platform) for url in self.channel_base_urls
        ]

    @property
    def environment_paths(self):
        ''' All known Anaconda environment paths

        paths to :ref:`Anaconda environments <environment>` are searched for in the directories specified by `config.locations`.
        Environments located elsewhere are unknown to Anaconda.
        '''
        env_paths = []
        for location in self.locations:
            if not exists(location):
                log.warning("location '%s' does not exist" % location)
                continue
            for fn in os.listdir(location):
                prefix = join(location, fn)
                if isdir(prefix):
                    env_paths.append(prefix)
        return sorted(env_paths)

    def __repr__(self):
        return 'config()'
