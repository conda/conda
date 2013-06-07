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
        'CONDA_ROOT': 'root_dir',
        'CONDA_PACKAGE_CACHE': 'pkgs_dir',
        'CONDA_ENV_PATH': 'envs_dir',
        'CONDA_DEFAULT_ENV': '_default_env',
        'CIO_TEST': 'base_urls',
        }

    def __init__(self):
        self.update_env_attrs()
        super(EnvironmentConfig, self).__init__()

    def update_env_attrs(self):
        for env in self.envmapping:
            attr = self.envmapping[env]
            result = os.getenv(env)
            if env == "CIO_TEST":
                self.base_urls = ['http://filer/pkgs/pro',
                    'http://filer/pkgs/free']
                if os.getenv('CIO_TEST') == '2':
                    self.base_urls.insert(0, 'http://filer/test-pkgs')
            else:
                if result is not None:
                    setattr(self, attr, result)

class RCConfigBase(ConfigBase):
    def __init__(self):
        if not self.rc_path or isfile(self.rc_path):
            self.rc_path = None
        self.load_condarc()
        super(RCConfigBase, self).__init__()

    rc_path = None

    def load_condarc(self):
        if not self.rc_path:
            self.rc = self.rc_path
        else:
            import yaml
            self.rc = yaml.load(open(self.rc_path))

            for attr in self.rc:
                if attr == "channels":
                    # "channels" in an rc file is actually base_urls
                    setattr(self, 'base_urls', self.rc[attr])
                else:
                    setattr(self, attr, self.rc[attr])

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
config_default = DefaultConfig()
config_rc = RCConfig()
