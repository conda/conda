# (c) 2012-2013 Continuum Analytics, Inc. / http://continuum.io
# All Rights Reserved
#
# conda is distributed under the terms of the BSD 3-clause license.
# Consult LICENSE.txt or http://opensource.org/licenses/BSD-3-Clause.

import os
import sys
import logging
from platform import machine
from os.path import abspath, expanduser, isfile, join

# The config system

# Each configuration location is represented by a class. The class should
# provide the configuration values as attributes.  If they need to be
# computed, use @property. If the @property function determines the property
# should not be defined in that function, return super(ClassName,
# self).attribute.  At the end, we create a Configuration class that
# subclasses from the superclasses in the precedence order of the
# configuration values.  Multiple inheritance and MRO magic take care of the
# precedence logic for us.

class ConfigBase(object):
    # def __init__(self):
    #     # Some common logic that must be applied regardless of where the
    #     # configuration value comes from
    #     from api import normalize_urls
    #     self.channels = normalize_urls(self.base_urls)
    #     super(ConfigBase, self).__init__()

    # Backwards compatibility. Remove.
    def get_channel_urls(self):
        from api import normalize_urls
        return normalize_urls(self.base_urls)

class UnconfigurableConfig(ConfigBase):
    # ----- operating system and architecture -----

    _sys_map = {'linux2': 'linux', 'linux': 'linux',
        'darwin': 'osx', 'win32': 'win'}
    platform = _sys_map.get(sys.platform, 'unknown')
    bits = 8 * tuple.__itemsize__

    if platform == 'linux' and machine() == 'armv6l':
        subdir = 'linux-armv6l'
        arch_name = 'armv6l'
    else:
        subdir = '%s-%d' % (platform, bits)
        arch_name = {64: 'x86_64', 32: 'x86'}[bits]

class DefaultConfig(ConfigBase):
    log = logging.getLogger(__name__)

    default_python = '2.7'
    default_numpy = '1.7'

    # ----- constant paths -----

    root_dir = sys.prefix

    @property
    def pkgs_dir(self):
        return join(self.root_dir, 'pkgs')

    @property
    def envs_dir(self):
        return join(self.root_dir, 'envs')

    # ----- default environment prefix -----

    _default_env = None

    @property
    def default_prefix(self):
        return self.root_dir

    base_urls = [
        'http://repo.continuum.io/pkgs/free',
        'http://repo.continuum.io/pkgs/pro',
    ]

class EnvironmentConfig(ConfigBase):
    # Note, the values of the environment variables only directly correspond
    # to the value of the config variable if no method with that name is
    # defined here.
    envmapping = {
        'root_dir': 'CONDA_ROOT',
        'pkgs_dir': 'CONDA_PACKAGE_CACHE',
        'envs_dir': 'CONDA_ENV_PATH',
        '_default_env': 'CONDA_DEFAULT_ENV',
        'base_urls': 'CIO_TEST',
        }

    def __getattr__(self, attr):
        result = os.getenv(self.envmapping[attr])
        if result is None:
            raise AttributeError

    @property
    def base_urls(self):
        if os.getenv('CIO_TEST'):
            base_urls = ['http://filer/pkgs/pro',
                'http://filer/pkgs/free']
            if os.getenv('CIO_TEST') == '2':
                base_urls.insert(0, 'http://filer/test-pkgs')
            return base_urls
        else:
            return super(EnvironmentConfig, self).base_urls

class RCConfigBase(ConfigBase):
    def __init__(self):
        if not self.rc_path or isfile(self.rc_path):
            self.rc_path = None
        self.rc = self.load_condarc(self.rc_path)
        super(RCConfigBase, self).__init__()

    rc_path = None

    def load_condarc(self, path):
        if not path:
            return path
        import yaml

        return yaml.load(open(path))

    def __getattr__(self, attr):
        return getattr(self.rc, attr)

class UserRCConfig(RCConfigBase):
    rc_path = abspath(expanduser('~/.condarc'))

class SystemRCConfig(RCConfigBase):
    rc_path = join(sys.prefix, '.condarc')

class RCConfig(UserRCConfig, SystemRCConfig):
    pass

# Add the configurations here in the precedence order
class Configuration(UnconfigurableConfig, EnvironmentConfig, RCConfig, DefaultConfig):
    pass

config = Configuration()
